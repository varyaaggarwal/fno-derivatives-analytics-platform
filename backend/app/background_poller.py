"""
In-process background poller.

WHAT THIS REPLACES: previously the only way to get live-ish data into
Supabase was to manually run nse_poller.py from your own laptop. That
can't react to "someone opened the app" -- nothing can, from a laptop
script. This module runs the same fetch loop *inside the deployed FastAPI
process itself*, started once automatically on server boot (see the
startup hook wired into main.py). As long as your Render service is
running, this loop is running -- no one has to do anything by hand.

HONEST CAVEAT (read this before assuming it "just works"):
This calls whichever backend app/data/data_source.py selects -- Upstox if
UPSTOX_ACCESS_TOKEN is set on Render, otherwise NSE directly (which, unlike
Upstox, does rate-limit/occasionally block cloud IP ranges regardless of
where the fetch runs from -- see live_nse_chain.py). What this loop fixes,
independent of which backend is active, is the "I can't predict when
they'll load the app" problem: it runs continuously regardless of whether
anyone is visiting, so by the time someone opens the dashboard there's
already a recent snapshot in Supabase for them to read (or, if the active
backend is failing, an honest data_source: mock instead of a crash). Two
things worth doing for real reliability:
  1. Use a Render plan that keeps the instance always-on (free-tier
     services spin down after inactivity, which pauses this loop too).
  2. Upstox access tokens expire daily (~3:30 AM IST) -- regenerate
     UPSTOX_ACCESS_TOKEN each trading morning, or this loop silently falls
     back to NSE (or mock, if NSE is also blocked) until you do.

Enable with the BACKGROUND_POLL=true env var (alongside SUPABASE_RELAY=true)
on your deployed backend.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.data import supabase_client
from app.data.market_hours import within_market_hours as _within_market_hours

logger = logging.getLogger("background_poller")

# Fixed UTC+5:30 offset -- IST has no daylight savings, so this is always
# correct regardless of what timezone the server itself is running in.
# BUG THIS FIXES (original bug, still relevant to the logging below):
# Render's containers run in UTC, not IST. An earlier version of this
# check used datetime.now() (server-local, i.e. UTC on Render) and
# compared it directly against 9:15/15:30 as if those were UTC hours -- so
# it was checking the wrong 6.25-hour window entirely and concluding
# "market closed" almost all real trading day.
IST = timezone(timedelta(hours=5, minutes=30))

POLL_INTERVAL_SECONDS = 30

# NOTE: the actual weekday+clock+holiday logic now lives in
# app/data/market_hours.py (imported above as _within_market_hours) so
# main.py's live-signal/SL-status endpoints and this poller can't drift out
# of sync with each other, and so the holiday check only has to be written
# once. This module keeps the same function name it always exposed so
# nothing else here has to change.


def _poll_symbol(symbol: str) -> bool:
    from app.data.data_source import fetch_flat_chain
    try:
        flat, backend = fetch_flat_chain(symbol)
        spot = flat.attrs["spot"]
        ok = supabase_client.cache_chain_snapshot(
            symbol=symbol, spot=float(spot),
            expiry_date=date.today() + timedelta(days=6),
            raw_rows=flat.round(4).to_dict(orient="records"),
        )
        logger.info("background poll %s: backend=%s spot=%s rows=%d supabase=%s", symbol, backend, spot, len(flat), ok)
        return ok
    except Exception as exc:
        # Never let a bad response take the server down -- log and move on,
        # the next loop iteration (or the mock fallback in main.py) covers it.
        logger.warning("background poll %s failed: %s", symbol, exc)
        return False


async def run_forever():
    """
    Fire-and-forget asyncio task, started once on app startup (see main.py).
    Polls NIFTY (for the chain/vol-surface/interpretation pages) and
    BANKNIFTY (for the DOS live-signal / SL-status strike lookups) every
    POLL_INTERVAL_SECONDS while the market is open; sleeps otherwise.
    """
    logger.info("Background NSE poller starting (interval=%ds)", POLL_INTERVAL_SECONDS)
    while True:
        try:
            if _within_market_hours():
                await asyncio.to_thread(_poll_symbol, "NIFTY")
                await asyncio.to_thread(_poll_symbol, "BANKNIFTY")
            else:
                logger.info("outside IST market hours (server time now: %s UTC, %s IST), idling",
                            datetime.utcnow().strftime("%H:%M"), datetime.now(IST).strftime("%H:%M"))
        except Exception:
            logger.exception("background poller loop crashed an iteration -- continuing")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
