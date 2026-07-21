"""
LIVE UPSTOX option chain fetcher -- the deployed-backend data source.

WHY UPSTOX INSTEAD OF NSE: nseindia.com's Akamai bot-management blocks/rate-
limits most cloud-provider IP ranges (Render, Railway, AWS, GCP...) regardless
of TLS fingerprint spoofing -- see live_nse_chain.py's docstring for the full
history of what was tried against NSE directly. Upstox's v2 REST API is a
documented, authenticated endpoint meant for exactly this kind of
server-to-server use, so it doesn't have that problem.

WHAT YOU NEED:
1. An Upstox developer account + access token. Generate one from
   https://upstox.com/developer/apps -- note that Upstox access tokens
   expire daily (around 3:30 AM IST), so a deployed backend needs this
   regenerated and re-set each trading day unless/until you wire up
   Upstox's refresh-token flow.
2. Set UPSTOX_ACCESS_TOKEN as an env var on your deployed backend (Render).
   That's the only switch: app/data/data_source.py automatically prefers
   this backend over live_nse_chain.py whenever the var is present, no
   other code change needed.

ENDPOINTS USED (Upstox API v2):
- GET /v2/option/contract?instrument_key=...                (available expiries)
- GET /v2/option/chain?instrument_key=...&expiry_date=...   (chain + Greeks)

Upstox already computes and returns IV/Greeks server-side per leg (see
"option_greeks" in the raw response), so unlike live_nse_chain.py this file
doesn't need iv_solver.py's Brent's-method fallback for the /api/chain and
/api/vol-surface routes -- those values come straight from Upstox.
iv_solver.py is untouched and still used wherever the code explicitly needs
to solve IV itself (e.g. the DOS module).
"""
import os
import time
from datetime import datetime, date as date_cls

import requests

UPSTOX_BASE = "https://api.upstox.com/v2"

# NSE index instrument keys for the underlying index's option chain
# (not any single expiry's futures contract).
INSTRUMENT_KEYS = {
    "NIFTY": "NSE_INDEX|Nifty 50",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
}

# How many of the nearest expiries to pull for the vol surface. Each extra
# expiry is one extra API call, so keep this small for a 30s poll loop.
VOL_SURFACE_NUM_EXPIRIES = 2

# Tiny in-memory cache so every poll (every 30s -- see background_poller.py)
# doesn't re-fetch the expiry list. Expiries only change weekly (Bank Nifty)
# / monthly (Nifty), so caching per (symbol, calendar day) is safe.
_expiry_cache = {}


def _access_token():
    token = os.getenv("UPSTOX_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("UPSTOX_ACCESS_TOKEN is not set")
    return token


def _headers():
    return {
        "Authorization": f"Bearer {_access_token()}",
        "Accept": "application/json",
    }


def _fetch_expiries(symbol: str):
    instrument_key = INSTRUMENT_KEYS[symbol]
    resp = requests.get(
        f"{UPSTOX_BASE}/option/contract",
        params={"instrument_key": instrument_key},
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    contracts = resp.json()["data"]
    today = date_cls.today()
    return sorted({
        datetime.strptime(c["expiry"], "%Y-%m-%d").date()
        for c in contracts
        if datetime.strptime(c["expiry"], "%Y-%m-%d").date() >= today
    })


def _nearest_expiry(symbol: str) -> str:
    cache_key = (symbol, date_cls.today())
    if cache_key in _expiry_cache:
        return _expiry_cache[cache_key]

    expiries = _fetch_expiries(symbol)
    if not expiries:
        raise RuntimeError(f"Upstox returned no upcoming expiries for {symbol}")
    nearest = expiries[0].strftime("%Y-%m-%d")
    _expiry_cache.clear()  # one entry at a time -- a single symbol is polled per call
    _expiry_cache[cache_key] = nearest
    return nearest


def fetch_option_chain(symbol="NIFTY", expiry_date=None, retries=2):
    """
    symbol: 'NIFTY' or 'BANKNIFTY'.
    Returns Upstox's raw JSON dict, with the resolved expiry/symbol stashed
    under "_expiry" / "_symbol" so normalize_* below don't need to re-derive
    them.
    Raises requests.HTTPError / RuntimeError if Upstox rejects the token or
    the request after retries.
    """
    if symbol not in INSTRUMENT_KEYS:
        raise ValueError(f"Unknown symbol for Upstox: {symbol}")
    instrument_key = INSTRUMENT_KEYS[symbol]
    expiry = expiry_date or _nearest_expiry(symbol)

    last_exc = None
    for attempt in range(retries):
        try:
            resp = requests.get(
                f"{UPSTOX_BASE}/option/chain",
                params={"instrument_key": instrument_key, "expiry_date": expiry},
                headers=_headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                body = resp.json()
                body["_expiry"] = expiry
                body["_symbol"] = symbol
                return body
            last_exc = requests.HTTPError(f"Upstox {resp.status_code}: {resp.text[:300]}")
        except requests.RequestException as exc:
            last_exc = exc
        time.sleep(1 * (attempt + 1))
    raise last_exc


def normalize_to_flat_chain(raw_json):
    """
    Converts Upstox's option-chain payload into the same flat schema
    mock_option_chain.py / live_nse_chain.py produce (strike, option_type,
    last_price, open_interest, implied_volatility) -- drop-in for app/core,
    nothing there needs to change.
    """
    import pandas as pd
    rows = []
    spot = None
    for entry in raw_json.get("data", []):
        strike = entry["strike_price"]
        if spot is None:
            spot = entry.get("underlying_spot_price")
        for side, key in (("call", "call_options"), ("put", "put_options")):
            leg = entry.get(key)
            if not leg:
                continue
            market = leg.get("market_data") or {}
            greeks = leg.get("option_greeks") or {}
            rows.append({
                "strike": strike,
                "option_type": side,
                "last_price": market.get("ltp", 0.0) or 0.0,
                "open_interest": market.get("oi", 0) or 0,
                "implied_volatility": greeks.get("iv", 0.0) or 0.0,
            })
    df = pd.DataFrame(rows)
    df.attrs["spot"] = spot
    df.attrs["timestamp"] = datetime.now().strftime("%d-%b-%Y %H:%M:%S")
    df.attrs["expiry"] = raw_json.get("_expiry")
    return df


def normalize_to_vol_surface(raw_json):
    """
    Upstox's option/chain endpoint is single-expiry-per-call (unlike NSE's
    option-chain-indices, which bundles every live expiry into one payload),
    so a real multi-expiry vol surface needs one extra call per additional
    expiry. Pulls VOL_SURFACE_NUM_EXPIRIES nearest expiries -- enough to show
    curvature across expiry without hammering the API on every 30s poll.
    Output schema matches mock_option_chain.generate_vol_surface(): strike,
    option_type, implied_volatility, expiry_days.
    """
    import pandas as pd

    symbol = raw_json.get("_symbol", "NIFTY")
    today = date_cls.today()
    expiries = _fetch_expiries(symbol)[:VOL_SURFACE_NUM_EXPIRIES]

    rows = []
    spot = None
    for expiry in expiries:
        expiry_str = expiry.strftime("%Y-%m-%d")
        raw = raw_json if expiry_str == raw_json.get("_expiry") else fetch_option_chain(symbol, expiry_date=expiry_str)
        expiry_days = max((expiry - today).days, 0)
        for entry in raw.get("data", []):
            strike = entry["strike_price"]
            if spot is None:
                spot = entry.get("underlying_spot_price")
            for side, key in (("call", "call_options"), ("put", "put_options")):
                leg = entry.get(key)
                if not leg:
                    continue
                iv = (leg.get("option_greeks") or {}).get("iv", 0.0)
                if iv:  # skip illiquid strikes Upstox returns 0 IV for -- they'd flatten the surface
                    rows.append({"strike": strike, "option_type": side,
                                 "implied_volatility": iv, "expiry_days": expiry_days})
    df = pd.DataFrame(rows)
    df.attrs["spot"] = spot
    return df


if __name__ == "__main__":
    raw = fetch_option_chain("NIFTY")
    chain = normalize_to_flat_chain(raw)
    print(chain.head(10))
    print("Spot:", chain.attrs["spot"])
