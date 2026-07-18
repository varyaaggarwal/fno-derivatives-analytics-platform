"""
P&L Decomposer: attributes a position's actual daily P&L to Delta, Gamma,
Theta, and Vega using a second-order Taylor expansion of the option price:

    dPrice ~= Delta*dS + 0.5*Gamma*dS^2 + Theta*dT + Vega*dSigma

where dS is the change in spot, dT is one trading day (already baked into
theta being a per-day figure), and dSigma is the change in IV (in vol points,
matching the *0.01 scaling already applied to vega in black_scholes.py).

A residual term captures higher-order effects (rho, cross-Greeks, discrete
jumps) that the linear/quadratic approximation misses -- this is reported
explicitly rather than hidden, since silently absorbing it into one Greek
would misattribute the P&L driver.
"""
import numpy as np
from .black_scholes import bs_price, greeks


def decompose_pnl(position, snapshot_t0, snapshot_t1):
    """
    position: dict with keys S, K, T, r, sigma, option_type, quantity (+ve=long, -ve=short)
              at snapshot_t0 (used to compute the Greeks the move is attributed against)
    snapshot_t0, snapshot_t1: dicts with keys S, T, sigma (spot, time-to-expiry, IV)
              at the start and end of the period being decomposed

    Returns a dict of contributions in premium terms, scaled by position quantity.
    """
    S0, T0, sigma0 = snapshot_t0["S"], snapshot_t0["T"], snapshot_t0["sigma"]
    S1, T1, sigma1 = snapshot_t1["S"], snapshot_t1["T"], snapshot_t1["sigma"]
    K, r, opt_type = position["K"], position["r"], position["option_type"]
    qty = position["quantity"]

    g = greeks(S0, K, T0, r, sigma0, option_type=opt_type)
    price0 = bs_price(S0, K, T0, r, sigma0, option_type=opt_type)
    price1 = bs_price(S1, K, T1, r, sigma1, option_type=opt_type)

    dS = S1 - S0
    d_sigma_pct = (sigma1 - sigma0) * 100  # vega is scaled per 1% (0.01) move
    days_elapsed = max(round((T0 - T1) * 365), 1)

    delta_pnl = float(g["delta"]) * dS
    gamma_pnl = 0.5 * float(g["gamma"]) * dS ** 2
    theta_pnl = float(g["theta"]) * days_elapsed
    vega_pnl = float(g["vega"]) * d_sigma_pct

    actual_pnl = float(price1 - price0)
    explained = delta_pnl + gamma_pnl + theta_pnl + vega_pnl
    residual = actual_pnl - explained

    contributions = {
        "delta_pnl": delta_pnl * qty,
        "gamma_pnl": gamma_pnl * qty,
        "theta_pnl": theta_pnl * qty,
        "vega_pnl": vega_pnl * qty,
        "residual_pnl": residual * qty,
        "actual_pnl": actual_pnl * qty,
        "price_t0": price0 * qty,
        "price_t1": price1 * qty,
    }
    driver = max(
        [("Delta", abs(contributions["delta_pnl"])),
         ("Gamma", abs(contributions["gamma_pnl"])),
         ("Theta", abs(contributions["theta_pnl"])),
         ("Vega", abs(contributions["vega_pnl"]))],
        key=lambda x: x[1],
    )[0]
    contributions["primary_driver"] = driver
    return contributions
