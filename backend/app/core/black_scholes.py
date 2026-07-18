"""
Vectorized Black-Scholes-Merton pricing and Greeks engine.

All functions accept scalars or numpy arrays and broadcast together, so a full
option chain (one row per strike) can be priced in a single call instead of
looping per-strike. This is the core pricing math referenced in the FnO deck:
    d1 = [ln(S/K) + (r - q + sigma^2/2) * T] / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)
    C  = S*e^(-qT)*N(d1) - K*e^(-rT)*N(d2)
    P  = K*e^(-rT)*N(-d2) - S*e^(-qT)*N(-d1)
"""
import numpy as np
from scipy.stats import norm

MIN_T = 1e-6      # floor for time-to-expiry to avoid div-by-zero on expiry day
MIN_SIGMA = 1e-4   # floor for volatility to avoid div-by-zero


def _d1_d2(S, K, T, r, sigma, q=0.0):
    S, K, T, r, sigma, q = (np.asarray(x, dtype=float) for x in (S, K, T, r, sigma, q))
    T = np.maximum(T, MIN_T)
    sigma = np.maximum(sigma, MIN_SIGMA)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return d1, d2


def bs_price(S, K, T, r, sigma, q=0.0, option_type="call"):
    """Black-Scholes-Merton price. option_type: 'call' or 'put'. Vectorized."""
    S, K, T, r, sigma, q = (np.asarray(x, dtype=float) for x in (S, K, T, r, sigma, q))
    T_safe = np.maximum(T, MIN_T)
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)

    call = S * np.exp(-q * T_safe) * norm.cdf(d1) - K * np.exp(-r * T_safe) * norm.cdf(d2)
    put = K * np.exp(-r * T_safe) * norm.cdf(-d2) - S * np.exp(-q * T_safe) * norm.cdf(-d1)

    is_call = np.asarray(option_type) == "call" if isinstance(option_type, np.ndarray) else (option_type == "call")
    if isinstance(is_call, bool):
        return call if is_call else put
    return np.where(is_call, call, put)


def greeks(S, K, T, r, sigma, q=0.0, option_type="call"):
    """
    Returns a dict of vectorized Greeks: delta, gamma, theta, vega, rho.
    - delta: price change per Re1 move in spot
    - gamma: rate of change of delta per Re1 move in spot
    - theta: price decay PER DAY (already divided by 365)
    - vega:  price change per 1% (0.01) move in IV
    - rho:   price change per 1% (0.01) move in the risk-free rate
    """
    S, K, T, r, sigma, q = (np.asarray(x, dtype=float) for x in (S, K, T, r, sigma, q))
    T_safe = np.maximum(T, MIN_T)
    sigma_safe = np.maximum(sigma, MIN_SIGMA)
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)

    is_call = np.asarray(option_type) == "call" if isinstance(option_type, np.ndarray) else np.full(np.broadcast(S, K).shape, option_type == "call")

    pdf_d1 = norm.pdf(d1)
    disc_q = np.exp(-q * T_safe)
    disc_r = np.exp(-r * T_safe)

    delta_call = disc_q * norm.cdf(d1)
    delta_put = disc_q * (norm.cdf(d1) - 1)
    delta = np.where(is_call, delta_call, delta_put)

    gamma = disc_q * pdf_d1 / (S * sigma_safe * np.sqrt(T_safe))

    vega = S * disc_q * pdf_d1 * np.sqrt(T_safe) * 0.01  # per 1% IV move

    theta_call = (
        -(S * disc_q * pdf_d1 * sigma_safe) / (2 * np.sqrt(T_safe))
        - r * K * disc_r * norm.cdf(d2)
        + q * S * disc_q * norm.cdf(d1)
    ) / 365.0
    theta_put = (
        -(S * disc_q * pdf_d1 * sigma_safe) / (2 * np.sqrt(T_safe))
        + r * K * disc_r * norm.cdf(-d2)
        - q * S * disc_q * norm.cdf(-d1)
    ) / 365.0
    theta = np.where(is_call, theta_call, theta_put)

    rho_call = K * T_safe * disc_r * norm.cdf(d2) * 0.01
    rho_put = -K * T_safe * disc_r * norm.cdf(-d2) * 0.01
    rho = np.where(is_call, rho_call, rho_put)

    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega, "rho": rho}


def price_and_greeks(S, K, T, r, sigma, q=0.0, option_type="call"):
    """Convenience: single call returning price + all Greeks for a strike array."""
    price = bs_price(S, K, T, r, sigma, q, option_type)
    g = greeks(S, K, T, r, sigma, q, option_type)
    g["price"] = price
    return g
