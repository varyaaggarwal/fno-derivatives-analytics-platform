"""
Unit tests for app/data/upstox_chain.py's normalizers, and for the
data_source router's backend-selection logic. No live Upstox call is made --
these test the parsing/routing logic against a hand-built fixture matching
Upstox API v2's documented option/chain response shape.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.data import upstox_chain, data_source


FAKE_UPSTOX_RESPONSE = {
    "status": "success",
    "_expiry": "2026-07-31",
    "_symbol": "NIFTY",
    "data": [
        {
            "strike_price": 24300,
            "underlying_spot_price": 24350.55,
            "call_options": {
                "market_data": {"ltp": 145.2, "oi": 125000},
                "option_greeks": {"iv": 13.5, "delta": 0.55, "gamma": 0.001, "theta": -8.2, "vega": 12.1},
            },
            "put_options": {
                "market_data": {"ltp": 98.7, "oi": 98000},
                "option_greeks": {"iv": 14.1, "delta": -0.45, "gamma": 0.001, "theta": -7.9, "vega": 12.4},
            },
        },
        {
            "strike_price": 24400,
            "underlying_spot_price": 24350.55,
            "call_options": {
                "market_data": {"ltp": 90.1, "oi": 140000},
                "option_greeks": {"iv": 13.9, "delta": 0.42, "gamma": 0.0012, "theta": -7.5, "vega": 12.8},
            },
            "put_options": {
                "market_data": {"ltp": 132.4, "oi": 110000},
                "option_greeks": {"iv": 14.4, "delta": -0.58, "gamma": 0.0012, "theta": -8.0, "vega": 13.0},
            },
        },
    ],
}


def test_normalize_to_flat_chain_schema_and_values():
    df = upstox_chain.normalize_to_flat_chain(FAKE_UPSTOX_RESPONSE)

    assert list(df.columns) == ["strike", "option_type", "last_price", "open_interest", "implied_volatility"]
    assert len(df) == 4  # 2 strikes x call/put
    assert set(df["option_type"]) == {"call", "put"}
    assert df.attrs["spot"] == 24350.55
    assert df.attrs["expiry"] == "2026-07-31"

    call_24300 = df[(df.strike == 24300) & (df.option_type == "call")].iloc[0]
    assert call_24300.last_price == 145.2
    assert call_24300.open_interest == 125000
    assert call_24300.implied_volatility == 13.5


def test_normalize_to_flat_chain_handles_missing_leg():
    """If Upstox omits a leg entirely (e.g. deep OTM strike pruned), don't crash."""
    sparse = {
        "_expiry": "2026-07-31",
        "_symbol": "NIFTY",
        "data": [{
            "strike_price": 25000,
            "underlying_spot_price": 24350.55,
            "call_options": {"market_data": {"ltp": 5.0, "oi": 500}, "option_greeks": {"iv": 15.0}},
            # no put_options key at all
        }],
    }
    df = upstox_chain.normalize_to_flat_chain(sparse)
    assert len(df) == 1
    assert df.iloc[0].option_type == "call"


def test_data_source_selects_upstox_when_token_present(monkeypatch):
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "fake-token-for-test")
    assert data_source.backend_name() == "upstox"


def test_data_source_falls_back_to_nse_without_token(monkeypatch):
    monkeypatch.delenv("UPSTOX_ACCESS_TOKEN", raising=False)
    assert data_source.backend_name() == "nse"
