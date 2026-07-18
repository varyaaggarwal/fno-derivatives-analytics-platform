"""
SuperTrend indicator, vectorized with pandas.

SuperTrend(period, multiplier) on OHLC candles:
    ATR = rolling average of True Range over `period` bars
    basic_upper = (high+low)/2 + multiplier*ATR
    basic_lower = (high+low)/2 - multiplier*ATR
    final bands "ratchet" toward price (never widen against the trend)
    trend flips when close crosses the opposite final band
"""
import numpy as np
import pandas as pd


def compute_supertrend(df, period=10, multiplier=3):
    """
    df: DataFrame with columns ['high', 'low', 'close'], datetime index.
    Returns df with added columns: 'atr', 'supertrend', 'trend' (+1 uptrend / -1 downtrend).
    """
    df = df.copy()
    hl2 = (df["high"] + df["low"]) / 2

    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr

    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    trend = pd.Series(1, index=df.index)  # start assuming uptrend
    supertrend = pd.Series(np.nan, index=df.index)

    for i in range(1, len(df)):
        # ratchet the bands: they only move in the direction favorable to the current trend
        if df["close"].iloc[i - 1] > final_upper.iloc[i - 1]:
            final_upper.iloc[i] = basic_upper.iloc[i]
        else:
            final_upper.iloc[i] = min(basic_upper.iloc[i], final_upper.iloc[i - 1])

        if df["close"].iloc[i - 1] < final_lower.iloc[i - 1]:
            final_lower.iloc[i] = basic_lower.iloc[i]
        else:
            final_lower.iloc[i] = max(basic_lower.iloc[i], final_lower.iloc[i - 1])

        if trend.iloc[i - 1] == 1:
            trend.iloc[i] = -1 if df["close"].iloc[i] < final_lower.iloc[i] else 1
        else:
            trend.iloc[i] = 1 if df["close"].iloc[i] > final_upper.iloc[i] else -1

        supertrend.iloc[i] = final_lower.iloc[i] if trend.iloc[i] == 1 else final_upper.iloc[i]

    df["atr"] = atr
    df["supertrend"] = supertrend
    df["trend"] = trend
    return df
