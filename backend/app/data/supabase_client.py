"""
Supabase persistence layer.

Wraps the tables defined in supabase/schema.sql:
  - option_chain_snapshots  (cache of each /api/chain fetch)
  - dos_trade_log           (persisted DOS backtest / live trades)

Deliberately fails soft: if SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY aren't
set (or the `supabase` package can't reach the project), every function here
becomes a no-op and logs a warning instead of crashing the API. This lets the
rest of the app run identically before you've created a Supabase project.
"""
import os
import logging
from datetime import datetime, date

logger = logging.getLogger("supabase_client")

_client = None
_client_checked = False


def get_client():
    """Lazily builds and caches the Supabase client. Returns None if unconfigured."""
    global _client, _client_checked
    if _client_checked:
        return _client
    _client_checked = True

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key or "YOUR-PROJECT-REF" in url:
        logger.warning("Supabase not configured (SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY missing) "
                        "-- persistence calls will be skipped.")
        return None
    try:
        from supabase import create_client
        _client = create_client(url, key)
        logger.info("Supabase client initialized against %s", url)
    except Exception as exc:  # noqa: BLE001 -- persistence must never take the API down
        logger.warning("Supabase client init failed: %s", exc)
        _client = None
    return _client


def is_configured() -> bool:
    return get_client() is not None


def cache_chain_snapshot(symbol: str, spot: float, expiry_date: date, raw_rows: list) -> bool:
    """Insert one row into option_chain_snapshots. Returns True on success."""
    client = get_client()
    if client is None:
        return False
    try:
        client.table("option_chain_snapshots").insert({
            "symbol": symbol,
            "fetched_at": datetime.utcnow().isoformat(),
            "spot": spot,
            "expiry_date": expiry_date.isoformat() if isinstance(expiry_date, date) else str(expiry_date),
            "raw_json": raw_rows,
        }).execute()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("cache_chain_snapshot failed: %s", exc)
        return False


def insert_dos_trades(trades: list) -> int:
    """
    Bulk-insert DOS trades (from the backtester or a live session) into
    dos_trade_log. Each dict should already match the table's columns
    (session_date, day_type, entry_time, exit_time, option_type, strike,
    fut_at_entry, fut_at_exit, supertrend_at_entry, premium_sold,
    premium_exit, exit_reason, pnl_rupees, delta_pnl, gamma_pnl, theta_pnl,
    vega_pnl, residual_pnl). Uses upsert on the table's unique constraint
    equivalent (session_date+entry_time here, since the schema itself has no
    explicit unique key on the trade log -- adjust if you add one).
    Returns the number of rows inserted, or 0 if skipped/failed.
    """
    client = get_client()
    if client is None or not trades:
        return 0
    try:
        client.table("dos_trade_log").insert(trades).execute()
        return len(trades)
    except Exception as exc:  # noqa: BLE001
        logger.warning("insert_dos_trades failed: %s", exc)
        return 0


def fetch_latest_chain_snapshot(symbol: str = "NIFTY", max_age_seconds: int = 120):
    """
    Reads back the most recent option_chain_snapshots row for `symbol`.
    Used by the SUPABASE_RELAY path in main.py so the deployed backend never
    calls NSE directly (see nse_poller.py for what writes these rows).

    Returns None if Supabase isn't configured, no row exists, or the latest
    row is older than max_age_seconds (stale -- caller should fall back to
    mock rather than show a frozen chain from an hour ago).
    """
    client = get_client()
    if client is None:
        return None
    try:
        res = (client.table("option_chain_snapshots")
               .select("*")
               .eq("symbol", symbol)
               .order("fetched_at", desc=True)
               .limit(1)
               .execute())
        if not res.data:
            return None
        row = res.data[0]
        fetched_at = datetime.fromisoformat(row["fetched_at"].replace("Z", "+00:00"))
        age = (datetime.now(fetched_at.tzinfo) - fetched_at).total_seconds()
        if age > max_age_seconds:
            logger.warning("Latest Supabase snapshot for %s is %.0fs old (>%ds) -- treating as stale",
                            symbol, age, max_age_seconds)
            return None
        return row
    except Exception as exc:  # noqa: BLE001
        logger.warning("fetch_latest_chain_snapshot failed: %s", exc)
        return None


def fetch_recent_dos_trades(limit: int = 100) -> list:
    """Read back the most recent persisted DOS trades (for a 'trade history from DB' view)."""
    client = get_client()
    if client is None:
        return []
    try:
        res = (client.table("dos_trade_log")
               .select("*")
               .order("session_date", desc=True)
               .limit(limit)
               .execute())
        return res.data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("fetch_recent_dos_trades failed: %s", exc)
        return []
