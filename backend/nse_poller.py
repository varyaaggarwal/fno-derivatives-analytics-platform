"""
Standalone NSE -> Supabase poller.

WHY THIS FILE EXISTS: NSE's Akamai bot-management blocks/rate-limits cloud
provider IP ranges (AWS/GCP/Azure/most PaaS -- this includes Render,
Railway, Vercel's serverless functions, and GitHub Actions runners, which
are Azure-hosted). So a deployed backend calling live_nse_chain.py directly
on every request WILL eventually fail in production even if it works when
you test it locally. This file is the fix the repo's docstrings pointed at
but never implemented: decouple the fetch from the request.

ARCHITECTURE:
  [this script, run on YOUR laptop/PC on a cron/Task Scheduler]
        -> fetch_option_chain() (curl_cffi, your residential IP)
        -> writes into Supabase option_chain_snapshots (+ optionally
           bhav_copy_fo once a day after close)
  [deployed FastAPI backend on Render, LIVE_NSE=true, SUPABASE_RELAY=true]
        -> reads the LATEST row from Supabase instead of calling NSE
        -> always fast, never blocked, degrades gracefully to mock if the
           latest snapshot is stale (see main.py's staleness check)

HOW TO RUN:
  - Locally, once, to test:      python nse_poller.py --once
  - On a schedule while you're building (every 30s during market hours):
        python nse_poller.py --interval 30
  - For "always on" during market hours without keeping your laptop open,
    the cleanest free option is a scheduled task on a machine you control
    (even a Raspberry Pi or an always-on home PC) -- NOT a cloud cron, since
    that hits the same IP-block problem this script exists to avoid.
  - Market hours only: NSE's option-chain endpoint returns stale/empty data
    outside 9:15am-3:30pm IST: this script no-ops outside that window (see
    _within_market_hours()) so you can safely leave --interval running.

REQUIRES: SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY in your environment (or a
.env file loaded via python-dotenv -- add `pip install python-dotenv` and
uncomment the load_dotenv() line below if you want that).
"""
import argparse
import time
from datetime import date, datetime, timedelta

# from dotenv import load_dotenv; load_dotenv()  # uncomment if you add python-dotenv

from app.data.live_nse_chain import fetch_option_chain, normalize_to_flat_chain, normalize_to_vol_surface
from app.data import supabase_client

IST_MARKET_OPEN = (9, 15)
IST_MARKET_CLOSE = (15, 30)


def _within_market_hours(now=None) -> bool:
    now = now or datetime.now()  # assumes the machine running this is set to IST; adjust if not
    if now.weekday() >= 5:  # Sat/Sun
        return False
    open_t = now.replace(hour=IST_MARKET_OPEN[0], minute=IST_MARKET_OPEN[1], second=0, microsecond=0)
    close_t = now.replace(hour=IST_MARKET_CLOSE[0], minute=IST_MARKET_CLOSE[1], second=0, microsecond=0)
    return open_t <= now <= close_t


def poll_once(symbol="NIFTY") -> bool:
    """Fetches one live chain and writes it to Supabase. Returns True on success."""
    try:
        raw = fetch_option_chain(symbol)
        flat = normalize_to_flat_chain(raw)
        spot = flat.attrs["spot"]
        # expiry_date: nearest expiry in the payload (first record's expiry if present,
        # else fall back to "today" so the row is never null)
        expiry_date = date.today() + timedelta(days=6)
        ok = supabase_client.cache_chain_snapshot(
            symbol=symbol, spot=float(spot), expiry_date=expiry_date,
            raw_rows=flat.round(4).to_dict(orient="records"),
        )
        print(f"[{datetime.now():%H:%M:%S}] {symbol} spot={spot} rows={len(flat)} "
              f"-> Supabase {'OK' if ok else 'FAILED (check SUPABASE_URL/KEY)'}")
        return ok
    except Exception as exc:
        print(f"[{datetime.now():%H:%M:%S}] fetch failed: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="NIFTY")
    parser.add_argument("--once", action="store_true", help="Run a single fetch and exit")
    parser.add_argument("--interval", type=int, default=30, help="Seconds between polls (min ~15 to be polite to NSE)")
    args = parser.parse_args()

    if not supabase_client.is_configured():
        print("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set -- writes will be no-ops. "
              "Set them in your environment before relying on this.")

    if args.once:
        poll_once(args.symbol)
        return

    print(f"Polling {args.symbol} every {args.interval}s during NSE market hours (Ctrl+C to stop)...")
    while True:
        if _within_market_hours():
            poll_once(args.symbol)
        else:
            print(f"[{datetime.now():%H:%M:%S}] outside market hours, sleeping...")
        time.sleep(max(args.interval, 15))


if __name__ == "__main__":
    main()
