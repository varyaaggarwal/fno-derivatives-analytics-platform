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
This still calls NSE from wherever the backend is deployed (Render), and
NSE's Akamai bot-management does rate-limit/occasionally block cloud IP
ranges -- that risk doesn't go away just because the fetch moved from your
laptop into the server process. What this DOES fix is the "I can't predict
when they'll load the app" problem: the loop runs continuously regardless
of whether anyone is visiting, so by the time someone opens the dashboard
there's already a recent snapshot in Supabase for them to read (or, if NSE
has been blocking Render's IP, an honest data_source: mock instead of a
crash). Two things worth doing for real reliability:
  1. Use a Render plan that keeps the instance always-on (free-tier
     services spin down after inactivity, which pauses this loop too).
  2. If Render's IP turns out to be reliably blocked, run nse_poller.py
     from your own machine as backup during your actual demo window --
     both write to the same Supabase table, so whichever one last
     succeeded is what gets served.

Enable with the BACKGROUND_POLL=true env var (alongside SUPABASE_RELAY=true)
on your deployed backend.
"""
import asyncio
import logging
from datetime import date, datetime, timedelta

from app.data import supabase_client

logger = logging.getLogger("background_poller")

IST_MARKET_OPEN = (9, 15)
IST_MARKET_CLOSE = (15, 30)
POLL_INTERVAL_SECONDS = 30


def _within_market_hours(now=None) -> bool:
    now = now or datetime.now()
    if now.weekday() >= 5:
        return False
    open_t = now.replace(hour=IST_MARKET_OPEN[0], minute=IST_MARKET_OPEN[1], second=0, microsecond=0)
    close_t = now.replace(hour=IST_MARKET_CLOSE[0], minute=IST_MARKET_CLOSE[1], second=0, microsecond=0)
    return open_t <= now <= close_t


def _poll_symbol(symbol: str) -> bool:
    from app.data.live_nse_chain import fetch_option_chain, normalize_to_flat_chain
    try:
        raw = fetch_option_chain(symbol)
        flat = normalize_to_flat_chain(raw)
        spot = flat.attrs["spot"]
        ok = supabase_client.cache_chain_snapshot(
            symbol=symbol, spot=float(spot),
            expiry_date=date.today() + timedelta(days=6),
            raw_rows=flat.round(4).to_dict(orient="records"),
        )
        logger.info("background poll %s: spot=%s rows=%d supabase=%s", symbol, spot, len(flat), ok)
        return ok
    except Exception as exc:
        # Never let a bad NSE response take the server down -- log and move on,
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
                logger.debug("outside market hours, idling")
        except Exception:
            logger.exception("background poller loop crashed an iteration -- continuing")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
