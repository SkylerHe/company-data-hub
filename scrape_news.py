#!/usr/bin/env python3
"""
scrape_news.py - Collect company news from Finnhub (free tier).

Finnhub's free plan includes the company-news endpoint (60 calls/min, US symbols
only). Get a free key at https://finnhub.io/register and export it:

    export FINNHUB_API_KEY='your_key_here'

Usage:
    python scrape_news.py                     # all stocks, last 30 days
    python scrape_news.py --company NVIDIA     # single instrument
    python scrape_news.py --days 7            # last 7 days (default 30)
    python scrape_news.py --asset-class all   # include ETFs/bonds/etc.

Notes:
- Free tier is US-exchange only; OTC ADRs (BYDDY, EADSY, ...) return a premium
  error. Those are reported at the end under "needs premium / no US listing",
  not counted as hard failures.
"""

import argparse
import os
import sys
import time
from datetime import datetime, timedelta

try:
    import requests
except ImportError:
    print("Error: requests not installed (pip install requests)")
    sys.exit(1)

import store


def _load_dotenv(path=".env"):
    """Load KEY=VALUE lines from a local .env into os.environ (without overriding
    values already set in the real environment). Keeps secrets out of the shell
    history and out of git — .env is git-ignored."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip("'\""))


_load_dotenv()
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY")
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"

# Finnhub uses different symbols than our DB for a few names (dotted class shares,
# and tickers it hasn't renamed). Map DB ticker -> Finnhub symbol.
FINNHUB_SYMBOL = {
    "BRK-B": "BRK.B",   # Berkshire class B uses a dot
    "FI": "FISV",       # Finnhub still lists Fiserv under its old ticker
}


def fetch_company_news(db, company, ticker, days=30):
    """Fetch news for one instrument. Returns a result dict with a 'premium' flag
    set when Finnhub blocks the symbol (non-US / needs a paid plan)."""
    result = {"new": 0, "seen": 0, "errors": 0, "premium": False}

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    params = {
        "symbol": FINNHUB_SYMBOL.get(ticker, ticker),
        "from": start_date.strftime("%Y-%m-%d"),
        "to": end_date.strftime("%Y-%m-%d"),
        "token": FINNHUB_API_KEY,
    }

    try:
        resp = requests.get(f"{FINNHUB_BASE_URL}/company-news", params=params, timeout=15)

        # Free tier blocks non-US symbols with 401/403 + "premium" message.
        if resp.status_code in (401, 403):
            print(f"  {company} ({ticker})... premium/not-US, skipped")
            result["premium"] = True
            return result
        resp.raise_for_status()

        articles = resp.json()
        if isinstance(articles, dict) and articles.get("error"):
            # e.g. {"error": "You don't have access to this resource."}
            print(f"  {company} ({ticker})... {articles['error'][:50]}")
            result["premium"] = True
            return result
        if not articles or not isinstance(articles, list):
            print(f"  {company} ({ticker})... no news")
            return result

        for a in articles:
            headline = (a.get("headline") or "").strip()
            url = (a.get("url") or "").strip()
            if not headline or not url:
                continue
            ts = a.get("datetime")
            date = (datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                    if ts else end_date.strftime("%Y-%m-%d"))
            source = a.get("source") or "Finnhub"
            content = a.get("summary") or headline

            new_id = store.add_news(db, company, source, url, headline, date, content)
            result["new" if new_id else "seen"] += 1

        print(f"  {company} ({ticker})... {result['new']} new, {result['seen']} seen")

    except requests.exceptions.RequestException as e:
        print(f"  {company} ({ticker})... ! API error: {str(e)[:60]}")
        result["errors"] = 1
    return result


def main():
    ap = argparse.ArgumentParser(description="Finnhub company-news scraper")
    ap.add_argument("--db", default=store.DB_PATH)
    ap.add_argument("--company", help="Scrape a single instrument by name")
    ap.add_argument("--days", type=int, default=30, help="Days of history (default 30)")
    ap.add_argument("--asset-class", default="stock",
                    help="Which instruments to cover: 'stock' (default), 'all', or a class")
    args = ap.parse_args()

    if not FINNHUB_API_KEY:
        print("Error: FINNHUB_API_KEY not set.\n")
        print("Get a free key (no card, ~1 min):")
        print("  1. https://finnhub.io/register")
        print("  2. export FINNHUB_API_KEY='your_key_here'")
        print("  3. re-run this script")
        sys.exit(1)

    print("Finnhub News Scraper")
    print("=" * 60)
    print(f"API key: {FINNHUB_API_KEY[:6]}...{FINNHUB_API_KEY[-4:]}\n")

    db = store.get_db(args.db)

    where = "ticker IS NOT NULL AND ticker != '' AND name != 'PORTFOLIO'"
    sql_params = []
    if args.asset_class != "all":
        where += " AND asset_class = ?"
        sql_params.append(args.asset_class)
    rows = db.execute(
        f"SELECT name, ticker FROM instruments WHERE {where} ORDER BY name", sql_params
    ).fetchall()

    if args.company:
        rows = [r for r in rows if r[0] == args.company]
        if not rows:
            print(f"'{args.company}' not found (or filtered out by --asset-class)")
            sys.exit(1)

    print(f"Collecting news for {len(rows)} instruments (last {args.days} days)...\n")
    totals = {"new": 0, "seen": 0, "errors": 0}
    premium = []
    for name, ticker in rows:
        r = fetch_company_news(db, name, ticker, args.days)
        for k in totals:
            totals[k] += r.get(k, 0)
        if r.get("premium"):
            premium.append(f"{name} ({ticker})")
        time.sleep(1)  # free tier: 60/min

    print("\n" + "=" * 60)
    print(f"New articles:  {totals['new']}")
    print(f"Already in DB: {totals['seen']}")
    print(f"Errors:        {totals['errors']}")
    if premium:
        print(f"\nNeeds premium / no US listing ({len(premium)}):")
        print("  " + ", ".join(premium))


if __name__ == "__main__":
    main()
