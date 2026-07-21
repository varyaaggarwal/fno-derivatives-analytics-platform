"""
FastAPI application. Wraps the pure-Python engine in app/core/ with HTTP
endpoints. Uses the mock data generators by default (LIVE_NSE=false) --
flip the env var once you've verified live_nse_chain.py / live_bnf_candles.py
work from a machine with real network access to nseindia.com and Yahoo
Finance (see those files' docstrings; this sandbox's network is restricted
to package registries and can't reach either, so LIVE_NSE=true has not been
exercised against the real internet here).

With LIVE_NSE=true: /api/chain and /api/vol-surface hit NSE's live
option-chain endpoint; /api/dos/live-signal and /api/dos/backtest pull real
5-min Bank Nifty index candles via yfinance. Every live path falls back to
its mock generator (and reports data_source/live_fetch_error in the
response) if the live fetch throws, so a flaky NSE/Yahoo response degrades
the dashboard instead of crashing it.
"""
import os
from datetime import date, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import numpy as np

from app.core.black_scholes import price_and_greeks
from app.core.iv_solver import solve_iv_chain
from app.core.interpretation import compute_pcr, pcr_card, compute_max_pain, max_pain_card, iv_spike_card, dos_trade_card
from app.core.pnl_decomposer import decompose_pnl
from app.core.backtester import run_backtest
from app.core.dos_strategy import initial_sl_price, trailing_sl_hit
from app.data.mock_option_chain import generate_chain, generate_vol_surface
from app.data.mock_bnf_candles import generate_dataset
from app.data import supabase_client

LIVE_NSE = os.getenv("LIVE_NSE", "false").lower() == "true"
SUPABASE_RELAY = os.getenv("SUPABASE_RELAY", "false").lower() == "true"
BACKGROUND_POLL = os.getenv("BACKGROUND_POLL", "false").lower() == "true"
RISK_FREE_RATE = 0.065

app = FastAPI(title="F&O Derivatives Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your Vercel domain before a real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_chain_df(expiry_days=6, spot=None):
    """Returns (df, data_source, live_fetch_error) so callers can be honest about which one they got."""
    if LIVE_NSE and SUPABASE_RELAY:
        # Deployed-backend-safe path: NSE blocks most cloud IPs (Render/Railway
        # included), so don't call NSE from here. Read the latest snapshot that
        # nse_poller.py (run from a real machine) has already written.
        import pandas as pd
        snapshot = supabase_client.fetch_latest_chain_snapshot("NIFTY", max_age_seconds=120)
        if snapshot is not None:
            df = pd.DataFrame(snapshot["raw_json"])
            df.attrs["spot"] = snapshot["spot"]
            return df, "live", None
        return (generate_chain(spot=spot or 24350.0, expiry_days=expiry_days), "mock",
                "no Supabase snapshot newer than 120s -- is nse_poller.py running?")
    if LIVE_NSE:
        from app.data.data_source import fetch_flat_chain
        try:
            df, backend = fetch_flat_chain("NIFTY")
            df.attrs.setdefault("expiry_days", expiry_days)
            return df, f"live-{backend}", None
        except Exception as exc:
            # Either backend can throw (NSE blocks/rate-limits cloud IPs,
            # Upstox tokens expire daily) -- degrade to mock instead of
            # 500ing the whole dashboard.
            live_fetch_error = str(exc)
            return generate_chain(spot=spot or 24350.0, expiry_days=expiry_days), "mock", live_fetch_error
    return generate_chain(spot=spot or 24350.0, expiry_days=expiry_days), "mock", None


def _apply_iv_solver(chain_df, spot, expiry_days):
    """
    Overwrites implied_volatility with our own reverse-BSM solve (Brent's
    method, iv_solver.solve_iv_chain) from last_price -- MVP requirement:
    "Implied Volatility solver using reverse Black-Scholes Model with
    Brent's method." Previously this function existed but nothing called
    it, so every IV shown came straight from the feed (NSE/Upstox/mock)
    instead of our own solver. Falls back to the feed's own IV wherever
    Brent's method can't bracket a root (e.g. a stale/zero last_price, or
    deep ITM/OTM where price is nearly insensitive to sigma).
    """
    T = expiry_days / 365.0
    solved = solve_iv_chain(
        chain_df["last_price"].values, spot, chain_df["strike"].values, T,
        RISK_FREE_RATE, chain_df["option_type"].values,
    )
    solved_pct = solved * 100
    feed_iv = chain_df["implied_volatility"].values
    out = chain_df.copy()
    out.attrs = chain_df.attrs
    out["implied_volatility"] = np.where(np.isnan(solved_pct), feed_iv, solved_pct)
    return out


def _enrich_with_greeks(chain_df, spot, expiry_days):
    T = expiry_days / 365.0
    calls = chain_df[chain_df.option_type == "call"].reset_index(drop=True)
    puts = chain_df[chain_df.option_type == "put"].reset_index(drop=True)
    for df, otype in ((calls, "call"), (puts, "put")):
        pg = price_and_greeks(spot, df.strike.values, T, RISK_FREE_RATE,
                               df.implied_volatility.values / 100, option_type=otype)
        df["theoretical_price"] = pg["price"]
        df["delta"], df["gamma"], df["theta"], df["vega"] = pg["delta"], pg["gamma"], pg["theta"], pg["vega"]
    import pandas as pd
    return pd.concat([calls, puts], ignore_index=True)


@app.on_event("startup")
async def _launch_background_poller():
    """
    Starts the NSE->Supabase background loop the instant this server process
    boots -- no one has to SSH in and run a script. Enable with
    BACKGROUND_POLL=true (alongside SUPABASE_RELAY=true) in your Render env
    vars. See app/background_poller.py for the honest caveats (Render
    free-tier spin-down, NSE's cloud-IP rate limiting).

    IMPORTANT: the task is stored on app.state, not discarded -- asyncio only
    holds a WEAK reference to tasks it runs; if nothing else references the
    task object, it can be garbage-collected mid-run with no error at all.
    Keeping app.state.poller_task alive for the life of the app prevents that.
    """
    if BACKGROUND_POLL:
        import asyncio
        from app.background_poller import run_forever
        app.state.poller_task = asyncio.create_task(run_forever())


@app.get("/api/health")
def health():
    poller_task = getattr(app.state, "poller_task", None)
    poller_status = "disabled"
    poller_error = None
    if poller_task is not None:
        if poller_task.done():
            poller_status = "crashed"
            try:
                poller_task.result()
            except Exception as exc:  # noqa: BLE001
                poller_error = str(exc)
        else:
            poller_status = "running"
    from app.data.data_source import backend_name
    return {"status": "ok", "live_nse": LIVE_NSE, "live_backend": backend_name() if LIVE_NSE else None,
            "supabase_configured": supabase_client.is_configured(),
            "supabase_relay": SUPABASE_RELAY, "background_poll": BACKGROUND_POLL,
            "poller_status": poller_status, "poller_error": poller_error}


@app.get("/api/chain")
def get_chain(expiry_days: int = 6, spot: float = 24350.0):
    """Option chain with Greeks for every strike -- MVP requirement #1 and #2."""
    chain, data_source, live_fetch_error = _get_chain_df(expiry_days, spot)
    actual_spot = chain.attrs.get("spot", spot)
    chain = _apply_iv_solver(chain, actual_spot, expiry_days)
    enriched = _enrich_with_greeks(chain, actual_spot, expiry_days)
    rows = enriched.round(4).to_dict(orient="records")

    # Cache the snapshot in Supabase (no-op if SUPABASE_URL isn't configured).
    symbol = "NIFTY" if data_source.startswith("live") else "MOCK_NIFTY"
    supabase_client.cache_chain_snapshot(
        symbol=symbol, spot=float(actual_spot),
        expiry_date=date.today() + timedelta(days=expiry_days), raw_rows=rows,
    )

    return {
        "spot": actual_spot,
        "expiry_days": expiry_days,
        "timestamp": chain.attrs.get("timestamp"),
        "rows": rows,
        "data_source": data_source,
        "live_fetch_error": live_fetch_error,
    }


@app.get("/api/vol-surface")
def get_vol_surface(spot: float = 24350.0):
    """Multi-expiry IV grid for the vol surface / smile view."""
    if LIVE_NSE:
        from app.data.data_source import fetch_vol_surface
        try:
            surface, backend = fetch_vol_surface("NIFTY")
            actual_spot = surface.attrs.get("spot", spot)
            return {"spot": actual_spot, "rows": surface.round(4).to_dict(orient="records"),
                    "data_source": f"live-{backend}"}
        except Exception as exc:
            # Fall through to mock rather than 500ing the dashboard -- either
            # backend can throw (NSE blocks, Upstox token expiry), see
            # live_nse_chain.py / upstox_chain.py docstrings.
            surface = generate_vol_surface(spot=spot)
            return {"spot": spot, "rows": surface.round(4).to_dict(orient="records"),
                    "data_source": "mock", "live_fetch_error": str(exc)}
    surface = generate_vol_surface(spot=spot)
    return {"spot": spot, "rows": surface.round(4).to_dict(orient="records"), "data_source": "mock"}


@app.get("/api/interpretation")
def get_interpretation(expiry_days: int = 6, spot: float = 24350.0):
    """PCR / Max Pain / IV Spike cards -- MVP requirement: at least two interpretation cards."""
    chain, _data_source, _live_fetch_error = _get_chain_df(expiry_days, spot)
    actual_spot = chain.attrs.get("spot", spot)
    pcr = compute_pcr(chain)
    max_pain = compute_max_pain(chain)
    atm_iv = chain.iloc[(chain.strike - actual_spot).abs().argsort()[:1]].implied_volatility.values[0]
    return {
        "pcr": pcr_card(pcr),
        "max_pain": max_pain_card(max_pain, actual_spot),
        "iv_spike": iv_spike_card(atm_iv, historical_avg_iv=13.5),
    }


@app.get("/api/pnl-decompose")
def get_pnl_decompose(strike: float = 24350, spot_move_pct: float = 0.8, iv_change_pts: float = 1.3,
                       expiry_days: int = 6, quantity: int = -50):
    """P&L decomposition for a sample position -- MVP requirement."""
    spot0 = 24350.0
    T0 = expiry_days / 365.0
    position = {"K": strike, "r": RISK_FREE_RATE, "option_type": "call", "quantity": quantity}
    snap_t0 = {"S": spot0, "T": T0, "sigma": 0.135}
    snap_t1 = {"S": spot0 * (1 + spot_move_pct / 100), "T": T0 - 1 / 365, "sigma": 0.135 + iv_change_pts / 100}
    result = decompose_pnl(position, snap_t0, snap_t1)
    return {k: (round(v, 2) if isinstance(v, (int, float, np.floating)) else v) for k, v in result.items()}


@app.get("/api/dos/backtest")
def get_dos_backtest(n_weeks: int = 8, persist: bool = False, use_bhav_copy: bool = False):
    """
    DOS strategy backtest -- MVP requires >= 4 weeks; default gives 8.
    Set persist=true to also write the trade log to Supabase's dos_trade_log
    table (off by default so repeated dashboard loads don't duplicate rows --
    call it explicitly, e.g. once per session, or wire a "Save to DB" button).
    Set use_bhav_copy=true to cross-check market-close exit premiums against
    the real NSE F&O Bhav Copy where a matching contract row exists (see
    app.core.backtester.run_backtest and app.data.live_bhav_copy).
    """
    data_source = "mock"
    live_fetch_error = None
    bnf_data = None
    if LIVE_NSE:
        from app.data.live_bnf_candles import fetch_expiry_day_history
        try:
            bnf_data = fetch_expiry_day_history(n_weeks=n_weeks)
            if bnf_data["session_date"].nunique() == 0:
                raise ValueError("no Wed/Thu sessions in the available window")
            data_source = "live"
        except Exception as exc:
            live_fetch_error = str(exc)
    if bnf_data is None:
        bnf_data = generate_dataset(n_weeks=n_weeks)
    trade_log, summary = run_backtest(bnf_data, use_bhav_copy=use_bhav_copy)
    trade_log_out = trade_log.copy()
    for col in ["session_date", "entry_time", "exit_time"]:
        trade_log_out[col] = trade_log_out[col].astype(str)
    trades = trade_log_out.to_dict(orient="records")
    for t in trades:
        t["interpretation"] = dos_trade_card(t)["note"]

    persisted_count = 0
    if persist:
        persisted_count = supabase_client.insert_dos_trades(trades)

    return {"summary": summary, "trades": trades,
            "persisted_to_supabase": persisted_count if persist else None,
            "data_source": data_source, "sessions_covered": int(bnf_data["session_date"].nunique()),
            "live_fetch_error": live_fetch_error}


@app.get("/api/dos/history")
def get_dos_history(limit: int = 100):
    """Reads back previously persisted DOS trades from Supabase (empty list if unconfigured)."""
    return {"trades": supabase_client.fetch_recent_dos_trades(limit=limit),
            "supabase_configured": supabase_client.is_configured()}


@app.get("/api/dos/live-signal")
def get_dos_live_signal():
    """
    Live DOS signal panel. When LIVE_NSE is on, pulls the current session's
    5-min Bank Nifty index candles (see live_bnf_candles.py for why the index
    stands in for the futures leg) and computes SuperTrend on the real feed.
    Falls back to a freshly generated mock session if the live fetch fails or
    the market hasn't produced a confirmed SuperTrend bar yet.
    """
    from app.core.supertrend import compute_supertrend
    from app.core.dos_strategy import select_strike, get_signal
    from app.core.black_scholes import bs_price
    from datetime import datetime, time as dtime

    today = datetime.now()
    # MVP: "active on Wednesday and Thursday only." Previously this endpoint
    # ran every day of the week and silently defaulted day_type to
    # "Wednesday" on Mon/Tue/Fri instead of reporting itself inactive.
    if today.weekday() not in (2, 3):  # Mon=0 .. Wed=2, Thu=3 .. Sun=6
        return {
            "active": False,
            "day_type": today.strftime("%A"),
            "bnf_fut": None, "supertrend": None, "trend": None, "signal": None,
            "recommended_strike": None, "recommended_premium": None,
            "is_mock": True, "live_fetch_error": None,
        }
    day_type = "Wednesday" if today.weekday() == 2 else "Thursday"

    is_mock = True
    live_fetch_error = None
    df = None
    if LIVE_NSE:
        from app.data.live_bnf_candles import fetch_live_session
        try:
            bnf_data = fetch_live_session()
            df = compute_supertrend(bnf_data, period=10, multiplier=3).dropna(subset=["supertrend"])
            if df.empty:
                raise ValueError("no confirmed SuperTrend bar yet this session")
            is_mock = False
        except Exception as exc:
            live_fetch_error = str(exc)

    if df is None:
        bnf_data = generate_dataset(n_weeks=1)
        df = compute_supertrend(bnf_data, period=10, multiplier=3).dropna(subset=["supertrend"])

    last = df.iloc[-1]
    signal = get_signal(last["close"], last["supertrend"])
    strike = select_strike(last["supertrend"]) if signal else None

    # MVP: "recommended CE or PE strike with premium on signal" -- previously
    # only the strike was computed, never the premium. Same-day (0DTE)
    # assumption and ASSUMED_IV, consistent with the backtester in
    # app/core/backtester.py (no live options premium feed available).
    premium = None
    if strike is not None:
        ASSUMED_IV = 0.14
        close_dt = datetime.combine(today.date(), dtime(15, 30))
        minutes_remaining = max((close_dt - today).total_seconds() / 60.0, 1.0)
        T = minutes_remaining / (375 * 252)
        bsm_type = "call" if signal == "CE" else "put"
        premium = round(float(bs_price(last["close"], strike, T, RISK_FREE_RATE, ASSUMED_IV, option_type=bsm_type)), 2)

    return {
        "active": True,
        "day_type": day_type,
        "bnf_fut": round(float(last["close"]), 1),
        "supertrend": round(float(last["supertrend"]), 1),
        "trend": "up" if last["trend"] == 1 else "down",
        "signal": signal,
        "recommended_strike": strike,
        "recommended_premium": premium,
        "is_mock": is_mock,
        "live_fetch_error": live_fetch_error,
    }


@app.get("/api/dos/sl-status")
def get_dos_sl_status(day_type: str, option_type: str, strike: float, entry_premium: float):
    """
    Live SL monitor for an open DOS position -- MVP requirement: "Stop-loss
    monitor tracking initial and trailing SL with live alerts." Previously
    this logic only ran inside the backtester; nothing tracked an open live
    position. The frontend calls this once a signal has been "entered"
    (recommended strike + entry premium from /api/dos/live-signal), passing
    that entry snapshot back on each poll.
    day_type: 'Wednesday' or 'Thursday' (sets the 50% vs 100% initial SL band).
    Returns current premium, both SL levels, and whether either is breached.
    """
    from app.core.supertrend import compute_supertrend
    from datetime import datetime as _dt

    is_mock = True
    live_fetch_error = None
    df = None
    if LIVE_NSE:
        from app.data.live_bnf_candles import fetch_live_session
        try:
            bnf_data = fetch_live_session()
            df = compute_supertrend(bnf_data, period=10, multiplier=3).dropna(subset=["supertrend"])
            if df.empty:
                raise ValueError("no confirmed SuperTrend bar yet")
            is_mock = False
        except Exception as exc:
            live_fetch_error = str(exc)
    if df is None:
        df = compute_supertrend(generate_dataset(n_weeks=1), period=10, multiplier=3).dropna(subset=["supertrend"])
    last = df.iloc[-1]

    current_premium = None
    premium_source = "mock"
    if LIVE_NSE and SUPABASE_RELAY:
        snapshot = supabase_client.fetch_latest_chain_snapshot("BANKNIFTY", max_age_seconds=120)
        if snapshot is not None:
            wanted_type = "call" if option_type == "CE" else "put"
            for row in snapshot["raw_json"]:
                if row.get("strike") == strike and row.get("option_type") == wanted_type:
                    current_premium = row.get("last_price")
                    premium_source = "live"
                    break
    if current_premium is None:
        current_premium = round(entry_premium * np.random.uniform(0.85, 1.15), 2)

    initial_sl = initial_sl_price(entry_premium, day_type)
    trailing_hit = trailing_sl_hit(last["supertrend"], option_type, last["close"])
    initial_hit = current_premium >= initial_sl

    return {
        "current_premium": current_premium,
        "premium_source": premium_source,
        "initial_sl_level": round(initial_sl, 2),
        "initial_sl_breached": bool(initial_hit),
        "trailing_sl_breached": bool(trailing_hit),
        "alert": bool(initial_hit or trailing_hit),
        "exit_reason": "initial_sl" if initial_hit else ("trailing_sl" if trailing_hit else None),
        "bnf_supertrend": round(float(last["supertrend"]), 1),
        "is_mock": is_mock or premium_source == "mock",
        "live_fetch_error": live_fetch_error,
        "checked_at": _dt.now().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
