"""
Market-hours check with holiday awareness.

WHY THIS EXISTS: background_poller.py's _within_market_hours() only checks
IST weekday + the 9:15-15:30 clock window -- it has no idea Diwali,
Republic Day, or any other NSE trading holiday isn't a trading day, so on
those dates it still treats the market as "open" all day. This module adds
a real holiday check on top of the same clock window, via Upstox's public
Market Holidays API, with the same "never crash, degrade gracefully"
contract as the rest of this codebase (see live_ws_feed.py, data_source.py).

FALLBACK: if the holiday API call fails (no network, Upstox endpoint down,
response shape changed) this falls back silently to the plain weekday +
clock check that background_poller.py already used before this file
existed. Worst case if this module breaks entirely: behaviour is identical
to before it existed -- never worse, never crashes the poller.

NOT VERIFIED END-TO-END: like live_ws_feed.py, the actual HTTP round trip
to Upstox's holiday endpoint has not been exercised from this sandbox (no
network path to api.upstox.com here). Written against Upstox's published
REST contract. Run the __main__ smoke test below against real network
access before relying on the holiday check for anything important:
    python -m app.data.market_hours
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

import requests

logger = logging.getLogger("market_hours")

# Same fixed UTC+5:30 offset background_poller.py uses -- IST has no
# daylight savings, so this is always correct regardless of the server's
# own timezone (Render's containers run in UTC).
IST = timezone(timedelta(hours=5, minutes=30))

IST_MARKET_OPEN = (9, 15)
IST_MARKET_CLOSE = (15, 30)

HOLIDAYS_URL = "https://api.upstox.com/v2/market/holidays"
# Holiday calendar doesn't change intraday -- no need to hit the API more
# than a few times a day even if this is called every poll cycle.
HOLIDAY_CACHE_TTL_SECONDS = 6 * 3600

_cache: dict = {"holidays": None, "fetched_at": None}


def _fetch_holiday_set() -> set | None:
    """Returns a set of 'YYYY-MM-DD' strings that are NSE trading holidays,
    or None if the fetch/parse failed for any reason (network, schema
    change, non-200, etc.) -- callers must treat None as "unknown", not
    "no holidays"."""
    try:
        resp = requests.get(HOLIDAYS_URL, headers={"Accept": "application/json"}, timeout=5)
        resp.raise_for_status()
        payload = resp.json().get("data", [])
        # Each entry is documented as {"date": "2026-10-21",
        # "holiday_type": "TRADING_HOLIDAY", "description": "...", ...}.
        # Some entries are non-trading-related (e.g. settlement-only days)
        # -- only full trading holidays should close the market for our
        # purposes, hence the explicit type filter rather than "any entry
        # on this date means closed."
        return {
            entry["date"] for entry in payload
            if entry.get("holiday_type", "TRADING_HOLIDAY") == "TRADING_HOLIDAY"
        }
    except Exception as exc:  # noqa: BLE001 -- must never break the caller
        logger.warning("holiday calendar fetch failed, falling back to clock-only check: %s", exc)
        return None


def _cached_holiday_set() -> set | None:
    now_utc = datetime.now(timezone.utc)
    stale = (
        _cache["fetched_at"] is None
        or (now_utc - _cache["fetched_at"]).total_seconds() > HOLIDAY_CACHE_TTL_SECONDS
    )
    if stale:
        _cache["holidays"] = _fetch_holiday_set()
        _cache["fetched_at"] = now_utc
    return _cache["holidays"]


def is_trading_day(now=None) -> bool:
    """Weekday check (pre-existing behaviour) AND NSE holiday check (new).
    If the holiday lookup is unavailable, degrades to weekday-only, which
    is exactly what background_poller.py did before this file existed."""
    now = now or datetime.now(IST)
    if now.weekday() >= 5:
        return False
    holidays = _cached_holiday_set()
    if holidays is not None and now.strftime("%Y-%m-%d") in holidays:
        return False
    return True


def within_market_hours(now=None) -> bool:
    """Drop-in replacement for background_poller._within_market_hours(),
    with the holiday check layered underneath. Same signature, same
    fail-safe guarantee: any failure inside is_trading_day's holiday
    lookup degrades to the plain weekday+clock check -- this function
    itself never raises."""
    now = now or datetime.now(IST)
    if not is_trading_day(now):
        return False
    open_t = now.replace(hour=IST_MARKET_OPEN[0], minute=IST_MARKET_OPEN[1], second=0, microsecond=0)
    close_t = now.replace(hour=IST_MARKET_CLOSE[0], minute=IST_MARKET_CLOSE[1], second=0, microsecond=0)
    return open_t <= now <= close_t


if __name__ == "__main__":
    # Local smoke test -- run against real network access before trusting
    # the holiday check: python -m app.data.market_hours
    logging.basicConfig(level=logging.INFO)
    holidays = _fetch_holiday_set()
    if holidays is None:
        print("Holiday fetch failed -- see the warning above. Falling back to clock-only check.")
    else:
        print(f"Fetched {len(holidays)} NSE trading holidays.")
        upcoming = sorted(h for h in holidays if h >= date.today().isoformat())[:5]
        print("Next few:", upcoming)
    print("within_market_hours() right now:", within_market_hours())
