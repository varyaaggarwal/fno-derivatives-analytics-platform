"""
Validation suite for the pricing engine. Run with: pytest -v

These are the sanity checks flagged in the architecture plan as necessary
before trusting the Greeks/IV numbers shown on the dashboard:
1. Put-call parity: C - P = S*e^-qT - K*e^-rT (must hold exactly, it's identity)
2. Known textbook BSM value (Hull's textbook example)
3. IV round-trip: price -> solve IV -> reprice must recover the same price
"""
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.black_scholes import bs_price, greeks
from app.core.iv_solver import solve_iv_single


def test_put_call_parity():
    S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.2
    call = bs_price(S, K, T, r, sigma, option_type="call")
    put = bs_price(S, K, T, r, sigma, option_type="put")
    lhs = call - put
    rhs = S - K * np.exp(-r * T)
    assert abs(lhs - rhs) < 1e-8, f"Put-call parity violated: {lhs} vs {rhs}"


def test_known_hull_value():
    # Hull's textbook example: S=42, K=40, r=10%, sigma=20%, T=0.5y -> call ~= 4.76
    price = bs_price(S=42, K=40, T=0.5, r=0.10, sigma=0.20, option_type="call")
    assert abs(price - 4.76) < 0.05, f"Expected ~4.76, got {price:.4f}"


def test_deep_itm_call_delta_near_one():
    d = greeks(S=200, K=100, T=0.25, r=0.05, sigma=0.2, option_type="call")["delta"]
    assert d > 0.95, f"Deep ITM call delta should approach 1, got {d}"


def test_deep_otm_put_delta_near_zero():
    d = greeks(S=200, K=100, T=0.25, r=0.05, sigma=0.2, option_type="put")["delta"]
    assert d > -0.05, f"Deep OTM put delta should approach 0, got {d}"


def test_gamma_positive_and_symmetric_atm():
    call_g = greeks(S=100, K=100, T=0.5, r=0.05, sigma=0.2, option_type="call")["gamma"]
    put_g = greeks(S=100, K=100, T=0.5, r=0.05, sigma=0.2, option_type="put")["gamma"]
    assert call_g > 0 and put_g > 0
    assert abs(call_g - put_g) < 1e-8  # gamma is identical for call/put at same strike


def test_iv_round_trip():
    S, K, T, r, sigma_true = 24000.0, 24000.0, 0.02, 0.065, 0.14
    for opt_type in ("call", "put"):
        market_price = bs_price(S, K, T, r, sigma_true, option_type=opt_type)
        solved_iv = solve_iv_single(market_price, S, K, T, r, opt_type)
        assert abs(solved_iv - sigma_true) < 1e-4, f"{opt_type}: expected {sigma_true}, got {solved_iv}"


def test_iv_solver_returns_nan_below_intrinsic():
    # A call priced below intrinsic value is an arbitrage-violating quote; must not solve
    iv = solve_iv_single(market_price=0.5, S=24500, K=24000, T=0.02, r=0.065, option_type="call")
    assert np.isnan(iv)


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
