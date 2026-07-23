"""
Structured data-provenance metadata for API responses.

WHY THIS EXISTS: every live-capable endpoint in main.py already tags its
response with a data_source string ("mock", "live-upstox", "live-nse") and
sometimes a live_fetch_error -- honest, but flat, and the frontend has to
re-derive "how stale is this?" and "what does this string actually mean?"
itself. This module turns that into one structured object any endpoint can
attach: which rung of the fallback ladder served the request, a
plain-English description of that source, an IST capture timestamp, and a
computed staleness flag.

ADDITIVE ONLY: this does not replace data_source/live_fetch_error --
existing frontend code (and test_upstox_chain.py-style checks) may already
depend on those flat fields. source_meta is a new key alongside them.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

# Matches the 120s freshness window already used elsewhere in this codebase
# (see supabase_client.fetch_latest_chain_snapshot's max_age_seconds default
# and main.py's SUPABASE_RELAY path) so "stale" means the same thing
# everywhere in the app, not a second, disagreeing definition.
STALE_AFTER_SECONDS = 120

_DESCRIPTIONS = {
    "live-upstox": "Live tick data from Upstox's REST/WebSocket feed",
    "live-nse": "Live option-chain scrape from NSE's public endpoint",
    "live": "Live data (specific upstream resolved elsewhere)",
    "mock": "Synthetically generated, NSE-shaped mock data",
}


def build_source_meta(data_source: str, captured_at: datetime = None,
                       live_fetch_error: str = None) -> dict:
    """
    data_source: one of the strings main.py already produces --
        "mock", "live", "live-nse", "live-upstox".
    captured_at: when this specific data point was actually generated or
        fetched. Defaults to now (IST) if the caller doesn't have a more
        precise timestamp (e.g. a WS tick's own ltt, or a Supabase
        snapshot's captured_at) -- pass the real one when you have it, or
        the staleness figure below is meaningless.
    live_fetch_error: pass through main.py's existing live_fetch_error
        field so "degraded" reflects a real fallback, not just "not live."
    """
    now = datetime.now(IST)
    captured_at = captured_at or now
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=IST)
    age_seconds = max((now - captured_at).total_seconds(), 0.0)

    description = _DESCRIPTIONS.get(
        data_source,
        _DESCRIPTIONS["live"] if data_source.startswith("live") else f"Unrecognized source: {data_source}",
    )

    return {
        "rung": data_source,
        "description": description,
        "captured_at": captured_at.isoformat(),
        "age_seconds": round(age_seconds, 1),
        "stale": age_seconds > STALE_AFTER_SECONDS,
        "degraded": live_fetch_error is not None,
        "live_fetch_error": live_fetch_error,
    }
