"""
DOS strategy backtester.

Runs the rules in dos_strategy.py across historical (mocked) 5-min BNF futures
sessions, pricing the sold option leg via Black-Scholes (since no historical
options premium feed is available -- see mock_bnf_candles.py docstring for
why). Produces a trade log + summary stats (win rate, avg P&L, SL hit rate)
and an equity curve, matching the MVP deliverable list.

ASSUMPTIONS (stated explicitly, not hidden -- flag these in your one-pager):
- Same-day (0DTE) expiry for both Wednesday and Thursday sessions
- Flat IV assumption of 14% per session (real IV would come from the live
  option chain snapshot at entry time; swap `ASSUMED_IV` for a live lookup)
- Lot size 15 (adjust LOT_SIZE if NSE's current BNF lot size differs)
- Risk-free rate 6.5%
"""
import numpy as np
import pandas as pd
from datetime import time, datetime, timedelta

from .supertrend import compute_supertrend
from .dos_strategy import select_strike, get_signal, initial_sl_price, trailing_sl_hit, entry_allowed
from .black_scholes import bs_price

ASSUMED_IV = 0.14
RISK_FREE_RATE = 0.065
LOT_SIZE = 15
MARKET_CLOSE = time(15, 30)
TRADING_MINUTES_PER_YEAR = 375 * 252


def _time_to_expiry_years(bar_time):
    close_dt = datetime.combine(bar_time.date(), MARKET_CLOSE)
    minutes_remaining = max((close_dt - bar_time).total_seconds() / 60.0, 1.0)
    return minutes_remaining / TRADING_MINUTES_PER_YEAR


def _option_premium(fut_price, strike, bar_time, option_type):
    T = _time_to_expiry_years(bar_time)
    bsm_type = "call" if option_type == "CE" else "put"
    return float(bs_price(fut_price, strike, T, RISK_FREE_RATE, ASSUMED_IV, option_type=bsm_type))


def run_backtest(raw_df):
    """
    raw_df: concatenated 5-min OHLC dataframe from mock_bnf_candles.generate_dataset(),
            with columns [timestamp, open, high, low, close, volume, day_type, session_date].
    Returns (trade_log_df, summary_dict).
    """
    df = raw_df.sort_values("timestamp").reset_index(drop=True)
    df = compute_supertrend(df, period=10, multiplier=3)

    trades = []
    for session_date, day_df in df.groupby("session_date"):
        day_type = day_df["day_type"].iloc[0]
        day_df = day_df.reset_index(drop=True)

        entry_idx = None
        for i, row in day_df.iterrows():
            if pd.isna(row["supertrend"]):
                continue
            if entry_allowed(row["timestamp"]) and get_signal(row["close"], row["supertrend"]) is not None:
                entry_idx = i
                break
        if entry_idx is None:
            continue  # no valid entry this session (rare, only if ST never confirms)

        entry_row = day_df.iloc[entry_idx]
        option_type = get_signal(entry_row["close"], entry_row["supertrend"])
        strike = select_strike(entry_row["supertrend"])
        premium_sold = _option_premium(entry_row["close"], strike, entry_row["timestamp"], option_type)
        sl_price = initial_sl_price(premium_sold, day_type)

        exit_reason, exit_row, premium_exit = None, None, None
        for j in range(entry_idx + 1, len(day_df)):
            row = day_df.iloc[j]
            current_premium = _option_premium(row["close"], strike, row["timestamp"], option_type)

            if current_premium >= sl_price:
                exit_reason, exit_row, premium_exit = "initial_sl", row, current_premium
                break
            if trailing_sl_hit(row["supertrend"], option_type, row["close"]):
                exit_reason, exit_row, premium_exit = "trailing_sl", row, current_premium
                break

        if exit_row is None:
            exit_row = day_df.iloc[-1]
            exit_reason = "market_close"
            premium_exit = _option_premium(exit_row["close"], strike, exit_row["timestamp"], option_type)

        pnl_points = premium_sold - premium_exit  # short position: profit if premium falls
        trades.append({
            "session_date": session_date, "day_type": day_type,
            "entry_time": entry_row["timestamp"], "exit_time": exit_row["timestamp"],
            "option_type": option_type, "strike": strike,
            "fut_at_entry": round(entry_row["close"], 1), "fut_at_exit": round(exit_row["close"], 1),
            "supertrend_at_entry": round(entry_row["supertrend"], 1),
            "premium_sold": round(premium_sold, 2), "premium_exit": round(premium_exit, 2),
            "exit_reason": exit_reason,
            "pnl_points": round(pnl_points, 2), "pnl_rupees": round(pnl_points * LOT_SIZE, 2),
        })

    trade_log = pd.DataFrame(trades)
    trade_log["cumulative_pnl"] = trade_log["pnl_rupees"].cumsum()

    summary = {
        "total_trades": len(trade_log),
        "win_rate_pct": round((trade_log["pnl_rupees"] > 0).mean() * 100, 1),
        "avg_pnl_rupees": round(trade_log["pnl_rupees"].mean(), 2),
        "total_pnl_rupees": round(trade_log["pnl_rupees"].sum(), 2),
        "sl_hit_rate_pct": round((trade_log["exit_reason"] != "market_close").mean() * 100, 1),
        "initial_sl_hits": int((trade_log["exit_reason"] == "initial_sl").sum()),
        "trailing_sl_hits": int((trade_log["exit_reason"] == "trailing_sl").sum()),
        "market_close_exits": int((trade_log["exit_reason"] == "market_close").sum()),
        "best_trade_rupees": round(trade_log["pnl_rupees"].max(), 2),
        "worst_trade_rupees": round(trade_log["pnl_rupees"].min(), 2),
    }
    return trade_log, summary
