"""
Upstox Market Data Feed V3 -- real-time WebSocket ingestion (opt-in, additive).

WHY THIS EXISTS: app/data/upstox_chain.py and data_source.py fetch the option
chain over REST, once per request (or once per poll interval, via
background_poller.py). That's polling. This module instead opens one
persistent WebSocket connection to Upstox's actual live feed and keeps an
in-process cache of the latest tick per instrument, updated the instant
Upstox pushes one -- push-based, not poll-based.

THIS DOES NOT REPLACE ANYTHING. It is off by default (WS_FEED_ENABLED unset
or "false") and every existing endpoint keeps working exactly as before if
you never touch this file's env var. When enabled, main.py's /api/chain
checks this module's cache FIRST and only falls through to the existing
REST/mock chain otherwise -- see the `latest_snapshot()` call added there.
If this module fails to connect, times out, or the token is rejected, it
logs and gives up gracefully; it never crashes the app and never blocks
startup (the connection attempt is a fire-and-forget asyncio task, same
pattern as background_poller.py).

PROTOCOL (Upstox Market Data Feed V3):
1. GET https://api.upstox.com/v3/feed/market-data-feed/authorize
   with `Authorization: Bearer <UPSTOX_ACCESS_TOKEN>` -> a one-time-use
   wss:// URL (`authorized_redirect_uri`), valid for a single connection.
2. Open that wss:// URL with a standard websocket client.
3. Send one binary-framed JSON `sub` request naming the instrumentKeys and
   mode ("full" gets LTP + OI + IV + Greeks in one message).
4. Every subsequent message is a **protobuf-encoded** `FeedResponse`
   (schema: app/data/MarketDataFeedV3_pb2.py, generated from Upstox's own
   .proto file in app/data/proto/ -- see that file's source: cloned directly
   from github.com/upstox/upstox-python, Upstox's official SDK repo, not
   reverse-engineered).
5. Upstox sends idle ping frames automatically; the `websockets` library
   answers pongs on its own, no manual keepalive needed for the socket
   itself (this is separate from the Render-sleep keepalive problem, which
   is about Render's HTTP layer spinning the whole container down, not the
   Upstox socket).

IMPORTANT -- NOT VERIFIED AGAINST A LIVE CONNECTION FROM HERE:
this was written against Upstox's published REST/WebSocket contract and the
official proto schema, and the protobuf decoding was verified to compile and
load, but the actual authorize -> connect -> subscribe -> decode round trip
against Upstox's live servers has NOT been run end-to-end in this
environment (no network path to api.upstox.com from the sandbox this was
written in). Test this yourself against your real token before relying on
it -- see the __main__ smoke test at the bottom of this file, run locally:
    python -m app.data.live_ws_feed
It connects, subscribes to NIFTY + BANKNIFTY indices, prints the first 5
decoded ticks, and exits. If that doesn't work cleanly, WS_FEED_ENABLED
should stay off and /api/chain will keep serving Upstox-REST/mock exactly
as it does today -- nothing regresses either way.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time

import requests
import websockets

from app.data import MarketDataFeedV3_pb2 as pb

logger = logging.getLogger("live_ws_feed")

AUTHORIZE_URL = "https://api.upstox.com/v3/feed/market-data-feed/authorize"


class AuthError(Exception):
    """Raised when Upstox rejects the token itself (401/403 on the
    authorize call) -- as opposed to a network blip, timeout, or a
    transient 5xx, which are just regular Exceptions and get the normal
    exponential-backoff retry below."""

# Same instrument-key convention as upstox_chain.py -- kept in sync manually
# since this module intentionally has zero imports from that file (it must
# be able to fail/be deleted without touching the REST path at all).
INSTRUMENT_KEYS = {
    "NIFTY": "NSE_INDEX|Nifty 50",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
}

RECONNECT_BACKOFF_START = 2.0
RECONNECT_BACKOFF_CAP = 60.0

# A bad/expired token will fail on every single retry until someone
# actually updates UPSTOX_ACCESS_TOKEN -- there's no backoff schedule that
# makes retrying every ~60s a good idea for that failure mode, it's just
# noise (and unnecessary load on Upstox's authorize endpoint). Park on this
# much longer, fixed interval instead once an AuthError is seen -- see
# run_forever().
AUTH_FAILED_RETRY_SECONDS = 300.0

# In-process latest-tick cache: instrument_key -> dict. Read by main.py via
# latest_snapshot(); written only by the loop below. No lock needed -- a
# single asyncio task is the sole writer, and dict item assignment is atomic
# under the GIL, which is all a single-writer/many-reader cache needs.
_latest: dict[str, dict] = {}
_status: dict = {
    "connected": False, "last_message_at": None, "last_error": None,
    # auth_failed=True means run_forever() has stopped normal retrying and
    # is parked on the long AUTH_FAILED_RETRY_SECONDS interval below --
    # see run_forever()'s docstring for why this is a separate state
    # rather than just another exception hitting the normal backoff.
    "auth_failed": False, "auth_failed_since": None,
}


def latest_snapshot(instrument_key: str) -> dict | None:
    """Read-only accessor for main.py. None if we've never received a tick
    for this key (feed not enabled, not yet connected, or index not subscribed)."""
    return _latest.get(instrument_key)


def feed_status() -> dict:
    """For /api/health -- surfaces connection state without exposing internals."""
    return dict(_status)


def _authorize(token: str) -> str:
    resp = requests.get(
        AUTHORIZE_URL,
        headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if resp.status_code in (401, 403):
        # Distinguish "this token is bad" from every other failure mode --
        # see AuthError's docstring and run_forever()'s handling below.
        raise AuthError(f"Upstox rejected the token ({resp.status_code}): {resp.text[:200]}")
    resp.raise_for_status()
    return resp.json()["data"]["authorized_redirect_uri"]


def _decode_tick(raw_bytes: bytes) -> dict | None:
    """Protobuf FeedResponse -> flat dict per instrument key we care about.
    Returns None for message types we don't need (e.g. market_info heartbeats)."""
    feed_response = pb.FeedResponse()
    feed_response.ParseFromString(raw_bytes)
    out = {}
    for instrument_key, feed in feed_response.feeds.items():
        full_feed = feed.fullFeed
        if full_feed.HasField("indexFF"):
            ltpc = full_feed.indexFF.ltpc
            out[instrument_key] = {"ltp": ltpc.ltp, "close": ltpc.cp, "ltt": ltpc.ltt}
        elif full_feed.HasField("marketFF"):
            m = full_feed.marketFF
            out[instrument_key] = {
                "ltp": m.ltpc.ltp, "close": m.ltpc.cp, "ltt": m.ltpc.ltt,
                "oi": m.oi, "iv": m.iv,
                "delta": m.optionGreeks.delta, "gamma": m.optionGreeks.gamma,
                "theta": m.optionGreeks.theta, "vega": m.optionGreeks.vega,
            }
    return out or None


async def _run_once(symbols: list[str]):
    token = os.getenv("UPSTOX_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("UPSTOX_ACCESS_TOKEN not set -- WS feed cannot authorize")

    ws_url = _authorize(token)
    instrument_keys = [INSTRUMENT_KEYS[s] for s in symbols if s in INSTRUMENT_KEYS]

    async with websockets.connect(ws_url, max_size=None) as ws:
        import json
        import uuid
        sub_request = {
            "guid": str(uuid.uuid4()),
            "method": "sub",
            "data": {"mode": "full", "instrumentKeys": instrument_keys},
        }
        await ws.send(json.dumps(sub_request).encode("utf-8"))
        _status.update(connected=True, last_error=None)
        logger.info("WS feed connected, subscribed to %s", instrument_keys)

        async for message in ws:
            decoded = _decode_tick(message)
            if decoded:
                _latest.update(decoded)
                _status["last_message_at"] = time.time()


async def run_forever(symbols: list[str] = ("NIFTY", "BANKNIFTY")):
    """Entry point wired into main.py's startup hook, mirroring
    background_poller.run_forever()'s fire-and-forget pattern -- same
    "never raise out of this function" contract, so it's safe to
    asyncio.create_task() it and never await it.

    TWO DIFFERENT FAILURE MODES, TWO DIFFERENT RESPONSES:
    - Network/timeout/5xx/websocket-disconnect errors are transient by
      nature -- these use the normal exponential backoff (2s -> 60s cap)
      since the very next attempt might just work.
    - An AuthError (token rejected, see _authorize) will fail identically
      on every retry until a human replaces UPSTOX_ACCESS_TOKEN. Retrying
      that every ~60s forever is pure noise -- both in the logs and as
      load on Upstox's authorize endpoint -- so instead this sets
      auth_failed=True (visible via feed_status(), surfaced in main.py's
      /api/live-spot) and parks on the much longer
      AUTH_FAILED_RETRY_SECONDS interval. It still never gives up
      permanently and never needs a restart -- fix the token on Render and
      the very next parked attempt reconnects and clears auth_failed on
      its own.
    """
    backoff = RECONNECT_BACKOFF_START
    while True:
        try:
            await _run_once(list(symbols))
            backoff = RECONNECT_BACKOFF_START  # clean disconnect -- reset backoff
            _status.update(auth_failed=False, auth_failed_since=None)
        except AuthError as exc:
            was_already_parked = _status["auth_failed"]
            _status.update(
                connected=False, last_error=str(exc), auth_failed=True,
                auth_failed_since=_status["auth_failed_since"] or time.time(),
            )
            if not was_already_parked:
                logger.warning(
                    "WS feed auth rejected -- parking retries every %.0fs until "
                    "UPSTOX_ACCESS_TOKEN is updated: %s", AUTH_FAILED_RETRY_SECONDS, exc,
                )
            await asyncio.sleep(AUTH_FAILED_RETRY_SECONDS)
        except Exception as exc:  # noqa: BLE001 -- must never take the app down
            _status.update(connected=False, last_error=str(exc))
            logger.warning("WS feed error, retrying in %.0fs: %s", backoff, exc)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, RECONNECT_BACKOFF_CAP)


if __name__ == "__main__":
    # Local smoke test -- run this yourself against your real token before
    # ever setting WS_FEED_ENABLED=true on Render:
    #   cd backend && UPSTOX_ACCESS_TOKEN=xxx python -m app.data.live_ws_feed
    logging.basicConfig(level=logging.INFO)

    async def _smoke_test():
        seen = 0
        token = os.getenv("UPSTOX_ACCESS_TOKEN")
        if not token:
            print("Set UPSTOX_ACCESS_TOKEN in your environment first.")
            return
        ws_url = _authorize(token)
        print(f"Authorized OK, connecting to {ws_url[:60]}...")
        import json
        import uuid
        async with websockets.connect(ws_url, max_size=None) as ws:
            keys = list(INSTRUMENT_KEYS.values())
            await ws.send(json.dumps({
                "guid": str(uuid.uuid4()), "method": "sub",
                "data": {"mode": "full", "instrumentKeys": keys},
            }).encode("utf-8"))
            print("Subscribed. Waiting for ticks (Ctrl+C to stop early)...")
            async for message in ws:
                decoded = _decode_tick(message)
                if decoded:
                    seen += 1
                    print(f"[{seen}]", decoded)
                if seen >= 5:
                    break

    asyncio.run(_smoke_test())
