"""
Live 5-min Bank Nifty candles via yfinance.

WHY yfinance AND NOT NSE DIRECTLY: neither the NSE option-chain API nor the
Bhav Copy archive exposes historical intraday (5-min) futures prices --
option-chain is a live snapshot only, Bhav Copy is EOD-only (see
mock_bnf_candles.py). A real BNF *futures* tick feed needs a broker API
(Kite Connect, Global Datafeeds, etc.). yfinance is the free source the
assignment's own "Data Sources" section names for underlying spot/OHLCV, so
this uses the Bank Nifty *index* (^NSEBANK) 5-min candles as a proxy for the
futures leg. Index and futures diverge by a small, mostly-stable basis
(cost of carry), so SuperTrend direction on the index is a reasonable stand
-in -- note this assumption explicitly in your one-pager.

LIMITS TO KNOW ABOUT:
- yfinance only serves 5m-interval data for the last ~60 days -- backtests
  requesting more history than that will silently get fewer weeks back than
  asked for; this module returns whatever it actually got.
- yfinance scrapes Yahoo Finance and can rate-limit or change response shape
  without notice. If this starts failing, check the installed `yfinance`
  version first (pip install -U yfinance) before assuming the code is wrong.
- Run from a machine with normal outbound internet access, same caveat as
  live_nse_chain.py -- some cloud sandboxes block Yahoo's endpoints too.
"""
import pandas as pd


def _clean_ohlc(raw, symbol="^NSEBANK"):
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    ts_col = "Datetime" if "Datetime" in df.columns else df.columns[0]
    df = df.rename(columns={
        ts_col: "timestamp", "Open": "open", "High": "high",
        "Low": "low", "Close": "close", "Volume": "volume",
    })[["timestamp", "open", "high", "low", "close", "volume"]]
    # yfinance timestamps come back tz-aware (UTC or exchange tz) -- normalize
    # to naive IST-local so downstream time comparisons (entry_allowed etc.) work.
    if getattr(df["timestamp"].dt, "tz", None) is not None:
        df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    return df.dropna(subset=["open", "high", "low", "close"])


def fetch_live_session(symbol="^NSEBANK"):
    """
    Most recent trading session's 5-min bars, for the live DOS signal panel.
    Returns a DataFrame shaped like mock_bnf_candles output (no day_type/
    session_date needed here -- the caller already knows "today").
    """
    import yfinance as yf
    raw = yf.download(symbol, period="1d", interval="5m", progress=False)
    if raw.empty:
        raise ValueError(f"yfinance returned no data for {symbol}")
    return _clean_ohlc(raw, symbol)


def fetch_expiry_day_history(symbol="^NSEBANK", n_weeks=8):
    """
    Up to `n_weeks` of past Wednesday+Thursday sessions, 5-min bars, for the
    backtester. Capped by yfinance's ~60-day 5m-interval window -- if fewer
    weeks are available than requested, this returns what it can and the
    caller/response should surface the actual count rather than assume it
    got all `n_weeks`.
    """
    import yfinance as yf
    days_needed = min(n_weeks * 7 + 7, 59)  # stay under yfinance's 60-day 5m cutoff
    raw = yf.download(symbol, period=f"{days_needed}d", interval="5m", progress=False)
    if raw.empty:
        raise ValueError(f"yfinance returned no data for {symbol}")
    df = _clean_ohlc(raw, symbol)

    df["weekday"] = df["timestamp"].dt.weekday
    df = df[df["weekday"].isin([2, 3])].copy()  # 2=Wed, 3=Thu
    df["day_type"] = df["weekday"].map({2: "Wednesday", 3: "Thursday"})
    df["session_date"] = df["timestamp"].dt.date
    return df.drop(columns=["weekday"])


if __name__ == "__main__":
    live = fetch_live_session()
    print(live.tail(5))
    hist = fetch_expiry_day_history(n_weeks=8)
    print(f"\nSessions found: {hist.session_date.nunique()}, bars: {len(hist)}")
