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


def generate_chain(spot=24350.0, expiry_days=6, strike_step=50, n_strikes_each_side=15, seed=7,
                    smile_curvature=22.0, iv_term_premium=0.0, noise_std=0.0006):
    """
    smile_curvature: coefficient on moneyness^2 -- with strikes only spanning
    ~+/-2.5% of spot (n_strikes_each_side * strike_step / spot), the old
    coefficient (0.9) produced a real smile signal of ~0.05 IV points at the
    wings, while noise_std=0.004 (0.4 points) was ~7x bigger than that --
    i.e. the "smile" was almost entirely noise, which is what made the 3D
    surface plot look like jagged, disconnected spikes instead of a smooth
    curve. 22.0 gives ~1.1-1.3 IV points of real wing-vs-ATM spread, an order
    of magnitude above noise_std, so the curvature is what actually shows.
    iv_term_premium: added flat across all strikes for a given expiry slice
    -- see generate_vol_surface, which is what actually varies the surface
    along the expiry axis (previously every expiry was identical).
    """
    rng = np.random.default_rng(seed)
    T = expiry_days / 365.0
    atm_strike = round(spot / strike_step) * strike_step
    strikes = [atm_strike + i * strike_step for i in range(-n_strikes_each_side, n_strikes_each_side + 1)]

    rows = []
    for K in strikes:
        moneyness = (K - spot) / spot
        base_iv = 0.13 + iv_term_premium + smile_curvature * moneyness ** 2 + rng.normal(0, noise_std)
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
    """
    Multiple expiries -> a strike x expiry IV grid for the 3D surface plot.

    BUG THIS FIXES: every expiry slice used to call generate_chain() with the
    *same* seed and no expiry-dependent term at all, so all 5 slices were
    byte-for-byte identical -- the surface was perfectly flat along the
    expiry axis, i.e. not actually 3D. Two changes here:
    1. `term_premium` decays from a modest near-term bump toward zero as
       expiry lengthens (short-dated index options commonly carry a bit more
       IV from event/gamma risk) -- this is what gives the surface real
       shape along the y-axis instead of a repeated identical smile.
    2. seed varies per expiry (seed + exp_days) so the small per-strike
       noise isn't identically repeated at every slice either.
    """
    frames = []
    for exp_days in expiries_days:
        term_premium = 0.012 * np.exp(-exp_days / 15.0)
        df = generate_chain(spot, exp_days, strike_step, n_strikes_each_side,
                             seed=seed + exp_days, iv_term_premium=term_premium)
        df["expiry_days"] = exp_days
        frames.append(df)
    return pd.concat(frames, ignore_index=True)
