"""
Single switch point between live data backends, so main.py /
background_poller.py / nse_poller.py don't each need their own
if-Upstox-else-NSE branching.

SELECTION RULE: if UPSTOX_ACCESS_TOKEN is set, use upstox_chain.py.
Otherwise fall back to live_nse_chain.py (direct NSE scrape). This is the
only place that decision is made -- everything else just calls
fetch_flat_chain() / fetch_vol_surface() below and gets a ready-to-use
DataFrame back, tagged with which backend actually served it.
"""
import os


def backend_name() -> str:
    return "upstox" if os.getenv("UPSTOX_ACCESS_TOKEN") else "nse"


def _backend_module():
    if backend_name() == "upstox":
        from app.data import upstox_chain
        return upstox_chain
    from app.data import live_nse_chain
    return live_nse_chain


def fetch_flat_chain(symbol="NIFTY"):
    """
    Returns (df, backend_name). df matches the mock_option_chain schema
    (strike, option_type, last_price, open_interest, implied_volatility),
    regardless of which backend produced it.
    """
    backend = _backend_module()
    raw = backend.fetch_option_chain(symbol)
    return backend.normalize_to_flat_chain(raw), backend_name()


def fetch_vol_surface(symbol="NIFTY"):
    """
    Returns (df, backend_name). df matches mock_option_chain.generate_vol_surface()
    (strike, option_type, implied_volatility, expiry_days).
    """
    backend = _backend_module()
    raw = backend.fetch_option_chain(symbol)
    return backend.normalize_to_vol_surface(raw), backend_name()
