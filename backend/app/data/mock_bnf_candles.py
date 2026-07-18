"""
Mock 5-minute Bank Nifty futures OHLC generator, shaped exactly like what you'd
get from a real intraday feed (columns: timestamp, open, high, low, close, volume).

WHY MOCK: NSE's live option-chain API and Bhav Copy don't provide historical
5-min intraday data (Bhav Copy is EOD-only); a real intraday history needs a
paid vendor (e.g. Kite Connect historical API, Global Datafeeds) or your own
recorded feed going forward. This generator produces statistically realistic
paths (correct intraday vol, correct trading hours) so the SuperTrend/DOS
logic can be built and demoed now -- swap this module's output for a real
vendor CSV later; nothing downstream needs to change.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def _expiry_wednesdays_thursdays(start_date, n_weeks):
    """Bank Nifty weekly expiry historically fell on Wed; using Wed+Thu pair per week per the assignment spec."""
    dates = []
    d = start_date
    while len(dates) < n_weeks * 2:
        if d.weekday() == 2:   # Wednesday
            dates.append((d, "Wednesday"))
        elif d.weekday() == 3:  # Thursday
            dates.append((d, "Thursday"))
        d += timedelta(days=1)
    return dates


def generate_bnf_futures_session(session_date, start_price, seed, annual_vol=0.16):
    """One trading day's 5-min candles, 9:15 AM to 3:30 PM IST (75 bars)."""
    rng = np.random.default_rng(seed)
    n_bars = 75  # (15:30 - 9:15) / 5min
    dt = 5 / (375 * 252)  # 5-min fraction of a trading year (375 min/day, 252 days/yr)
    sigma_bar = annual_vol * np.sqrt(dt)

    drift = rng.normal(0, 0.0003)  # small random daily directional bias
    rets = rng.normal(drift, sigma_bar, n_bars)
    closes = start_price * np.exp(np.cumsum(rets))

    opens = np.concatenate([[start_price], closes[:-1]])
    intrabar_vol = sigma_bar * 0.6
    highs = np.maximum(opens, closes) * (1 + np.abs(rng.normal(0, intrabar_vol, n_bars)))
    lows = np.minimum(opens, closes) * (1 - np.abs(rng.normal(0, intrabar_vol, n_bars)))
    volumes = rng.integers(5000, 40000, n_bars)

    timestamps = [datetime.combine(session_date, datetime.min.time()) + timedelta(hours=9, minutes=15) + timedelta(minutes=5 * i)
                  for i in range(n_bars)]

    return pd.DataFrame({
        "timestamp": timestamps, "open": opens, "high": highs, "low": lows,
        "close": closes, "volume": volumes,
    }), closes[-1]


def generate_dataset(start_date=datetime(2026, 5, 1), n_weeks=8, start_price=51000.0, seed=42):
    """
    Full mock dataset across n_weeks of Wed+Thu expiry-day sessions.
    Returns a dict: {date_str: DataFrame} plus a flat concatenated DataFrame.
    """
    sessions = _expiry_wednesdays_thursdays(start_date, n_weeks)
    all_frames = []
    price = start_price
    for i, (session_date, day_name) in enumerate(sessions):
        df, price = generate_bnf_futures_session(session_date, price, seed=seed + i)
        df["day_type"] = day_name
        df["session_date"] = session_date.date()
        all_frames.append(df)
    full = pd.concat(all_frames, ignore_index=True)
    return full


if __name__ == "__main__":
    df = generate_dataset()
    print(df.head(10))
    print(f"\nTotal sessions: {df.session_date.nunique()}, total bars: {len(df)}")
