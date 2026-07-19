"""
NSE Bhav Copy (EOD derivatives data) downloader.

MANUAL STEP: NSE changed its Bhav Copy archive path/format a few times over
the years (old .csv, then .csv.zip, now the "UDiFF" combined file format on
nsearchives.nseindia.com). By the time you build this, verify the current
exact URL pattern by opening NSE's official archive page in a browser network
tab and copying the real request -- don't trust any hardcoded URL (including
the one below) without checking it first, these break silently.

Uses curl_cffi (browser TLS impersonation) for the warm-up hit against
www.nseindia.com, same reasoning as live_nse_chain.py -- plain `requests`
gets fingerprinted and blocked by Akamai before the cookie is even issued.
"""
from curl_cffi import requests
import pandas as pd
from datetime import datetime
from io import BytesIO
from zipfile import ZipFile

IMPERSONATE = "chrome124"


def download_bhavcopy_fo(date: datetime):
    """
    Downloads and parses the F&O Bhav Copy for a given date.
    VERIFY THIS URL PATTERN AGAINST NSE'S CURRENT ARCHIVE BEFORE RELYING ON IT.
    """
    date_str = date.strftime("%Y%m%d")
    url = f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{date_str}_F_0000.csv.zip"

    session = requests.Session(impersonate=IMPERSONATE)
    session.get("https://www.nseindia.com", timeout=10)  # cookie warm-up, same as live chain

    resp = session.get(url, timeout=15)
    resp.raise_for_status()

    with ZipFile(BytesIO(resp.content)) as zf:
        csv_name = zf.namelist()[0]
        with zf.open(csv_name) as f:
            df = pd.read_csv(f)
    return df


if __name__ == "__main__":
    df = download_bhavcopy_fo(datetime(2026, 7, 3))
    print(df.head())
