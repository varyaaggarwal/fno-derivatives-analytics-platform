"""
LIVE NSE option chain fetcher. Run this from your own machine/server, NOT from
a cloud sandbox with no outbound access to nseindia.com.

Why the session warm-up matters: NSE's API rejects requests that don't carry
cookies from a prior homepage hit, and blocks generic User-Agents / missing
Referer headers. Hitting the API cold gets you a 401/403.

WHAT YOU NEED TO DO MANUALLY:
1. Run this from a machine with normal internet access (your laptop, or a
   normal cloud VM — NOT this sandbox).
2. NSE aggressively rate-limits and occasionally blackholes cloud-provider IP
   ranges (AWS/GCP/Azure) even with correct headers. If you deploy the
   backend on Render/Railway and this starts silently failing, that's why —
   options are (a) cache aggressively and poll every 3-5s instead of on every
   request, (b) run this specific fetcher on a small residential-IP box (e.g.
   your own PC via a scheduled task) and have it push into Supabase, with
   the deployed backend only ever reading from Supabase, never hitting NSE
   directly.
3. No API key needed — this is the public endpoint the NSE website itself
   uses. Don't hammer it faster than ~1 req/3sec per symbol or you'll get
   temporarily blocked.
"""
import requests
import time

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "application/json, text/plain, */*",
}


def _get_session():
    """Warm-up hit to the homepage to receive the cookies the API requires."""
    session = requests.Session()
    session.headers.update(BASE_HEADERS)
    session.get("https://www.nseindia.com", timeout=5)
    time.sleep(1)  # NSE flags requests that come in too fast after the warm-up
    return session


def fetch_option_chain(symbol="NIFTY", retries=3):
    """
    symbol: 'NIFTY' or 'BANKNIFTY'.
    Returns the raw NSE JSON (dict) with keys like 'records' -> 'data' -> [...].
    Raises requests.HTTPError if NSE blocks/rate-limits after retries.
    """
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    session = _get_session()
    for attempt in range(retries):
        resp = session.get(url, timeout=8, headers={"Referer": f"https://www.nseindia.com/option-chain"})
        if resp.status_code == 200:
            return resp.json()
        time.sleep(2 * (attempt + 1))
        session = _get_session()  # refresh cookies and retry
    resp.raise_for_status()


def normalize_to_flat_chain(raw_json):
    """
    Converts NSE's nested JSON into the same flat schema mock_option_chain.py
    produces (strike, option_type, last_price, open_interest, implied_volatility),
    so this is a drop-in replacement -- nothing in core/ needs to change.
    """
    import pandas as pd
    rows = []
    for record in raw_json["records"]["data"]:
        strike = record["strikePrice"]
        for side, key in (("call", "CE"), ("put", "PE")):
            if key in record:
                leg = record[key]
                rows.append({
                    "strike": strike,
                    "option_type": side,
                    "last_price": leg.get("lastPrice", 0.0),
                    "open_interest": leg.get("openInterest", 0),
                    "implied_volatility": leg.get("impliedVolatility", 0.0),
                })
    df = pd.DataFrame(rows)
    df.attrs["spot"] = raw_json["records"]["underlyingValue"]
    df.attrs["timestamp"] = raw_json["records"]["timestamp"]
    return df


def normalize_to_vol_surface(raw_json):
    """
    NSE's option-chain-indices response actually carries every live expiry in
    one payload (each record has an 'expiryDate', and records.expiryDates
    lists them all) -- so the 3D vol surface needs no extra requests, just a
    regroup of the same JSON fetch_option_chain() already returns.
    Output schema matches mock_option_chain.generate_vol_surface(): strike,
    option_type, implied_volatility, expiry_days.
    """
    import pandas as pd
    from datetime import datetime

    timestamp = raw_json["records"]["timestamp"]
    as_of = datetime.strptime(timestamp, "%d-%b-%Y %H:%M:%S")

    rows = []
    for record in raw_json["records"]["data"]:
        strike = record["strikePrice"]
        expiry_date = datetime.strptime(record["expiryDate"], "%d-%b-%Y")
        expiry_days = max((expiry_date - as_of).days, 0)
        for side, key in (("call", "CE"), ("put", "PE")):
            if key in record:
                leg = record[key]
                iv = leg.get("impliedVolatility", 0.0)
                if iv:  # NSE returns 0 for illiquid strikes -- skip, they'd flatten the surface
                    rows.append({"strike": strike, "option_type": side,
                                 "implied_volatility": iv, "expiry_days": expiry_days})
    df = pd.DataFrame(rows)
    df.attrs["spot"] = raw_json["records"]["underlyingValue"]
    return df


if __name__ == "__main__":
    raw = fetch_option_chain("NIFTY")
    chain = normalize_to_flat_chain(raw)
    print(chain.head(10))
    print("Spot:", chain.attrs["spot"])
