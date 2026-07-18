"""
Mock NIFTY option chain snapshot, field-matched to NSE's real option-chain
JSON response shape (strikePrice, openInterest, lastPrice, impliedVolatility
under CE/PE keys) so swapping this for a live `requests` call against
NSE later requires no changes to any code downstream of `to_flat_dataframe()`.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from ..core.black_scholes import bs_price

RISK_FREE_RATE = 0.065


def generate_chain(spot=24350.0, expiry_days=6, strike_step=50, n_strikes_each_side=15, seed=7):
    rng = np.random.default_rng(seed)
    T = expiry_days / 365.0
    atm_strike = round(spot / strike_step) * strike_step
    strikes = [atm_strike + i * strike_step for i in range(-n_strikes_each_side, n_strikes_each_side + 1)]

    rows = []
    for K in strikes:
        moneyness = (K - spot) / spot
        base_iv = 0.13 + 0.9 * moneyness ** 2 + rng.normal(0, 0.004)  # smile: higher IV away from ATM
        base_iv = max(base_iv, 0.08)

        call_price = float(bs_price(spot, K, T, RISK_FREE_RATE, base_iv, option_type="call"))
        put_price = float(bs_price(spot, K, T, RISK_FREE_RATE, base_iv, option_type="put"))

        call_oi = int(rng.integers(2000, 60000) * (1.4 if K >= atm_strike else 0.8))
        put_oi = int(rng.integers(2000, 60000) * (1.4 if K <= atm_strike else 0.8))

        rows.append({"strike": K, "option_type": "call", "last_price": round(call_price, 2),
                      "open_interest": call_oi, "implied_volatility": round(base_iv * 100, 2)})
        rows.append({"strike": K, "option_type": "put", "last_price": round(put_price, 2),
                      "open_interest": put_oi, "implied_volatility": round(base_iv * 100, 2)})

    df = pd.DataFrame(rows)
    df.attrs["spot"] = spot
    df.attrs["expiry_days"] = expiry_days
    df.attrs["timestamp"] = datetime.now().isoformat()
    return df


def generate_vol_surface(spot=24350.0, expiries_days=(6, 13, 20, 27, 34), strike_step=50, n_strikes_each_side=12, seed=7):
    """Multiple expiries -> a strike x expiry IV grid for the 3D surface plot."""
    frames = []
    for exp_days in expiries_days:
        df = generate_chain(spot, exp_days, strike_step, n_strikes_each_side, seed=seed)
        df["expiry_days"] = exp_days
        frames.append(df)
    return pd.concat(frames, ignore_index=True)
