"""
Implied Volatility solver: reverse Black-Scholes using Brent's method.

Given a market price, finds the sigma that makes bs_price(sigma) == market_price.
Uses scipy.optimize.brentq (bracketed root finder implementing Brent's method)
per strike, since it converges reliably without needing derivatives.
"""
import numpy as np
from scipy.optimize import brentq
from .black_scholes import bs_price

IV_LOWER_BOUND = 0.001   # 0.1% floor
IV_UPPER_BOUND = 5.0     # 500% ceiling (covers extreme event-day IV spikes)


def solve_iv_single(market_price, S, K, T, r, option_type="call", q=0.0):
    """
    Solve IV for a single option. Returns np.nan if no solution exists in bounds
    (e.g. price below intrinsic value, or deep ITM/OTM where vega is ~0 and the
    price is insensitive to sigma across the whole bracket).
    """
    if T <= 0 or market_price <= 0:
        return np.nan

    intrinsic = max(S - K, 0) if option_type == "call" else max(K - S, 0)
    if market_price < intrinsic - 1e-6:
        return np.nan  # arbitrage-violating quote, can't solve

    def objective(sigma):
        return bs_price(S, K, T, r, sigma, q, option_type) - market_price

    try:
        lo, hi = objective(IV_LOWER_BOUND), objective(IV_UPPER_BOUND)
        if lo * hi > 0:
            return np.nan  # same sign at both bounds -> no root bracketed
        return brentq(objective, IV_LOWER_BOUND, IV_UPPER_BOUND, xtol=1e-6, maxiter=100)
    except (ValueError, RuntimeError):
        return np.nan


def solve_iv_chain(market_prices, S, strikes, T, r, option_types, q=0.0):
    """
    Solve IV for an entire option chain (array of strikes). Not vectorizable
    inside brentq itself (it's a per-root iterative solver), but this loops
    over a small strike array (~20-40 strikes) which is cheap in practice.
    Returns a numpy array of IVs (np.nan where unsolvable).
    """
    market_prices = np.atleast_1d(market_prices)
    strikes = np.atleast_1d(strikes)
    option_types = np.atleast_1d(option_types)
    n = len(strikes)
    T = np.broadcast_to(T, (n,))
    r = np.broadcast_to(r, (n,))
    q = np.broadcast_to(q, (n,))

    ivs = np.empty(n)
    for i in range(n):
        ivs[i] = solve_iv_single(
            market_prices[i], S, strikes[i], T[i], r[i], str(option_types[i]), q[i]
        )
    return ivs
