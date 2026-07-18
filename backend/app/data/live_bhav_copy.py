"""
NSE Bhav Copy (EOD derivatives data) downloader.

MANUAL STEP: NSE changed its Bhav Copy archive path/format a few times over
the years (old .csv, then .csv.zip, now the "UDiFF" combined file format on
nsearchives.nseindia.com). By the time you build this, verify the current
exact URL pattern by opening NSE's official archive page in a browser network
tab and copying the real request -- don't trust any hardcoded URL (including
the one below) without checking it first, these break silently.
"""
import requests
import pandas as pd
from datetime import datetime
from io import BytesIO
from zipfile import ZipFile

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}


def download_bhavcopy_fo(date: datetime):
    """
    Downloads and parses the F&O Bhav Copy for a given date.
    VERIFY THIS URL PATTERN AGAINST NSE'S CURRENT ARCHIVE BEFORE RELYING ON IT.
    """
    date_str = date.strftime("%Y%m%d")
    url = f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{date_str}_F_0000.csv.zip"

    session = requests.Session()
    session.headers.update(BASE_HEADERS)
    session.get("https://www.nseindia.com", timeout=5)  # cookie warm-up, same as live chain

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
