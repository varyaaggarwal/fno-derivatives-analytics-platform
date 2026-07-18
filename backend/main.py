"""
FastAPI application. Wraps the pure-Python engine in app/core/ with HTTP
endpoints. Uses the mock data generators by default (LIVE_NSE=false) --
flip the env var once you've verified live_nse_chain.py works from a
machine with real network access to nseindia.com (see that file's docstring).
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
from app.data.mock_option_chain import generate_chain, generate_vol_surface
from app.data.mock_bnf_candles import generate_dataset
from app.data import supabase_client

LIVE_NSE = os.getenv("LIVE_NSE", "false").lower() == "true"
RISK_FREE_RATE = 0.065

app = FastAPI(title="F&O Derivatives Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your Vercel domain before a real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_chain_df(expiry_days=6, spot=None):
    if LIVE_NSE:
        from app.data.live_nse_chain import fetch_option_chain, normalize_to_flat_chain
        raw = fetch_option_chain("NIFTY")
        df = normalize_to_flat_chain(raw)
        df.attrs.setdefault("expiry_days", expiry_days)
        return df
    return generate_chain(spot=spot or 24350.0, expiry_days=expiry_days)


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


@app.get("/api/health")
def health():
    return {"status": "ok", "live_nse": LIVE_NSE, "supabase_configured": supabase_client.is_configured()}


@app.get("/api/chain")
def get_chain(expiry_days: int = 6, spot: float = 24350.0):
    """Option chain with Greeks for every strike -- MVP requirement #1 and #2."""
    chain = _get_chain_df(expiry_days, spot)
    actual_spot = chain.attrs.get("spot", spot)
    enriched = _enrich_with_greeks(chain, actual_spot, expiry_days)
    rows = enriched.round(4).to_dict(orient="records")

    # Cache the snapshot in Supabase (no-op if SUPABASE_URL isn't configured).
    symbol = "NIFTY" if LIVE_NSE else "MOCK_NIFTY"
    supabase_client.cache_chain_snapshot(
        symbol=symbol, spot=float(actual_spot),
        expiry_date=date.today() + timedelta(days=expiry_days), raw_rows=rows,
    )

    return {
        "spot": actual_spot,
        "expiry_days": expiry_days,
        "timestamp": chain.attrs.get("timestamp"),
        "rows": rows,
    }


@app.get("/api/vol-surface")
def get_vol_surface(spot: float = 24350.0):
    """Multi-expiry IV grid for the vol surface / smile view."""
    surface = generate_vol_surface(spot=spot)
    return {"spot": spot, "rows": surface.round(4).to_dict(orient="records")}


@app.get("/api/interpretation")
def get_interpretation(expiry_days: int = 6, spot: float = 24350.0):
    """PCR / Max Pain / IV Spike cards -- MVP requirement: at least two interpretation cards."""
    chain = _get_chain_df(expiry_days, spot)
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
def get_dos_backtest(n_weeks: int = 8, persist: bool = False):
    """
    DOS strategy backtest -- MVP requires >= 4 weeks; default gives 8.
    Set persist=true to also write the trade log to Supabase's dos_trade_log
    table (off by default so repeated dashboard loads don't duplicate rows --
    call it explicitly, e.g. once per session, or wire a "Save to DB" button).
    """
    bnf_data = generate_dataset(n_weeks=n_weeks)
    trade_log, summary = run_backtest(bnf_data)
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
            "persisted_to_supabase": persisted_count if persist else None}


@app.get("/api/dos/history")
def get_dos_history(limit: int = 100):
    """Reads back previously persisted DOS trades from Supabase (empty list if unconfigured)."""
    return {"trades": supabase_client.fetch_recent_dos_trades(limit=limit),
            "supabase_configured": supabase_client.is_configured()}


@app.get("/api/dos/live-signal")
def get_dos_live_signal():
    """
    Mock 'live' DOS signal panel using the most recent bar of a freshly
    generated mock session, standing in for a real-time feed until you wire
    live_nse_chain.py / a live futures feed in from your own machine.
    """
    from app.core.supertrend import compute_supertrend
    from app.core.dos_strategy import select_strike, get_signal
    from datetime import datetime

    today = datetime.now()
    day_type = "Wednesday" if today.weekday() == 2 else "Thursday" if today.weekday() == 3 else "Wednesday"
    bnf_data = generate_dataset(n_weeks=1)
    df = compute_supertrend(bnf_data, period=10, multiplier=3)
    last = df.dropna(subset=["supertrend"]).iloc[-1]

    signal = get_signal(last["close"], last["supertrend"])
    strike = select_strike(last["supertrend"]) if signal else None
    return {
        "day_type": day_type,
        "bnf_fut": round(float(last["close"]), 1),
        "supertrend": round(float(last["supertrend"]), 1),
        "trend": "up" if last["trend"] == 1 else "down",
        "signal": signal,
        "recommended_strike": strike,
        "is_mock": True,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
