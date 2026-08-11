#!/usr/bin/env python3
"""
scrape_ibkr.py - Collect data from Interactive Brokers API

Collects:
1. Fundamental data (revenue, EPS, margins, ratios)
2. Daily price & volume
3. Analyst estimates
4. IBKR news feed

Requirements:
- IBKR account (paper or live)
- TWS or IB Gateway running on localhost:7497
- ib_insync library: pip install ib_insync

Usage:
    python scrape_ibkr.py                      # collect all data for all companies
    python scrape_ibkr.py --company NVIDIA     # single company
    python scrape_ibkr.py --fundamentals-only  # just fundamentals
    python scrape_ibkr.py --prices-only        # just daily prices
    python scrape_ibkr.py --news-only          # just news feed
"""

import argparse
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from ib_insync import IB, Stock, util
except ImportError:
    print("Error: ib_insync not installed")
    print("Install with: pip install ib_insync")
    sys.exit(1)

import store

# IBKR connection settings
IBKR_HOST = "127.0.0.1"
IBKR_PORT = 4001  # IB Gateway Paper: 4001 (Gateway Live: 4002, TWS: 7496/7497)
CLIENT_ID = 1


def connect_ibkr():
    """Connect to IBKR TWS or Gateway."""
    ib = IB()
    try:
        ib.connect(IBKR_HOST, IBKR_PORT, clientId=CLIENT_ID, timeout=10)
        print(f"✓ Connected to IBKR at {IBKR_HOST}:{IBKR_PORT}")
        return ib
    except Exception as e:
        print(f"✗ Failed to connect to IBKR: {e}")
        print("\nMake sure TWS or IB Gateway is running:")
        print("  - TWS Paper Trading: localhost:7497")
        print("  - TWS Live Trading: localhost:7496")
        print("  - IB Gateway: localhost:4001 (paper) or 4002 (live)")
        sys.exit(1)


# IBKR uses its own symbology for a few names — notably a SPACE for share-class
# suffixes (Berkshire class B is "BRK B", not "BRK-B"). We keep our stored ticker
# as-is everywhere else; this map is applied ONLY for the IBKR contract lookup.
IBKR_SYMBOL_MAP = {
    "BRK-B": "BRK B",
    # Fiserv rebranded FISV -> FI, but IBKR's contract DB still lists it under the
    # legacy NASDAQ symbol FISV; 'FI' resolves to nothing on SMART. Keep our stored
    # ticker 'FI'; look it up as 'FISV'. (Verified: conId 269315, FISERV INC.)
    "FI": "FISV",
}


def _years_to_yf_period(years):
    """Map an IBKR-style history depth (int years) to the nearest valid yfinance
    period string. yfinance only accepts a fixed set (1/2/5/10y, ytd, max), so we
    round UP to the smallest window that still covers the requested depth — this
    guarantees a rotting ticker gets fully backfilled on the next run."""
    for y, period in ((1, "1y"), (2, "2y"), (5, "5y"), (10, "10y")):
        if years <= y:
            return period
    return "max"


def get_contract(ib, ticker):
    """Create and qualify a stock contract. `ticker` is our stored symbol;
    translate to IBKR's symbology where they differ (e.g. class shares)."""
    symbol = IBKR_SYMBOL_MAP.get(ticker, ticker)
    stock = Stock(symbol, 'SMART', 'USD')
    contracts = ib.qualifyContracts(stock)
    if not contracts:
        extra = f" (IBKR symbol '{symbol}')" if symbol != ticker else ""
        print(f"  ! Could not qualify contract for {ticker}{extra}")
        return None
    return contracts[0]


def fetch_fundamentals(ib, db, company, ticker):
    """IBKR fundamentals are intentionally NOT stored — we skip them.

    IBKR only returns fundamentals as a raw XML blob, and the `metrics` table has
    no column to hold it. The old code tried to pass that XML as an 8th positional
    argument to store.add_metric() (which takes 7), so every call raised and zero
    rows were ever stored — just 2 errors logged per instrument. Real fundamentals
    already come from Yahoo/Finviz (current snapshot) and SEC/EDGAR (statement
    trend), so IBKR's are redundant. Skip cleanly instead of erroring on every name.

    To revive this properly, parse the XML into its own table (e.g. `filings`)
    rather than `metrics`.
    """
    print(f"  Skipping IBKR fundamentals for {company} ({ticker}) — sourced from Yahoo/Finviz/EDGAR")
    return {"new": 0, "errors": 0, "skipped": 1}


def fetch_prices(ib, db, company, ticker, years=5):
    """Fetch historical daily prices (default: 5 years)."""
    print(f"  Fetching prices for {company} ({ticker}) - last {years} years...")

    contract = get_contract(ib, ticker)
    if not contract:
        # IBKR can't resolve this symbol AT ALL — a PERMANENT failure (bad or
        # renamed ticker), distinct from transient IB Gateway flakiness (a down
        # gateway fails to connect in main() and never reaches here). Left alone,
        # such a ticker silently rots for weeks (exactly how Fiserv 'FI' went stale
        # until we mapped it to 'FISV'). Fall back to Yahoo so the instrument keeps
        # updating and the gap is visible in the summary. Lazy import so a missing
        # yfinance degrades to one error here instead of aborting the whole run.
        print(f"    → IBKR could not qualify {ticker}; falling back to Yahoo")
        try:
            from scrape_yahoo import fetch_yahoo_prices
        except Exception as e:
            print(f"    ! Yahoo fallback unavailable: {e}")
            return {"new": 0, "errors": 1, "fallbacks": 1}
        r = fetch_yahoo_prices(db, company, ticker, period=_years_to_yf_period(years))
        r["fallbacks"] = 1
        if r.get("new", 0) == 0:
            # Bad on IBKR *and* Yahoo — this one genuinely needs a human to look.
            r["errors"] = r.get("errors", 0) or 1
        return r

    result = {"new": 0, "errors": 0}

    try:
        # Get daily bars for specified years
        # IBKR supports: '1 D', '1 W', '1 M', '1 Y', '5 Y' etc.
        bars = ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr=f'{years} Y',
            barSizeSetting='1 day',
            whatToShow='TRADES',
            useRTH=True,
            formatDate=1
        )
        
        for bar in bars:
            date = bar.date.strftime('%Y-%m-%d')
            
            # Store OHLCV as separate metrics
            store.add_metric(db, company, 'price_open', date, bar.open, 'USD', 'IBKR')
            store.add_metric(db, company, 'price_high', date, bar.high, 'USD', 'IBKR')
            store.add_metric(db, company, 'price_low', date, bar.low, 'USD', 'IBKR')
            store.add_metric(db, company, 'price_close', date, bar.close, 'USD', 'IBKR')
            store.add_metric(db, company, 'volume', date, bar.volume, 'shares', 'IBKR')
            result["new"] += 5

        print(f"    ✓ Stored {len(bars)} days of price data")
        if bars:
            store.recompute_moving_averages(db, company)  # refresh 20/50/200-day SMAs

    except Exception as e:
        print(f"    ! Error fetching prices: {e}")
        result["errors"] += 1
    
    return result


def fetch_analyst_estimates(ib, db, company, ticker):
    """IBKR analyst estimates are intentionally NOT stored — we skip them.

    Same root cause as fetch_fundamentals(): IBKR returns estimates as a raw XML
    blob with no home in the `metrics` table, and the old store.add_metric() call
    passed 8 args to a 7-arg function, so it always raised (1 error per instrument)
    and stored nothing. Skip cleanly; revive by parsing the XML into a real table.
    """
    print(f"  Skipping IBKR analyst estimates for {company} ({ticker})")
    return {"new": 0, "errors": 0, "skipped": 1}


def fetch_ibkr_news(ib, db, company, ticker, days=7):
    """Fetch IBKR news feed for a stock."""
    print(f"  Fetching IBKR news for {company} ({ticker})...")
    
    contract = get_contract(ib, ticker)
    if not contract:
        return {"errors": 1}
    
    result = {"new": 0, "errors": 0}
    
    try:
        # Request news articles
        news_providers = ib.reqNewsProviders()
        
        # Get recent news (past week)
        start = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d %H:%M:%S')
        end = datetime.now().strftime('%Y%m%d %H:%M:%S')
        
        news_articles = ib.reqHistoricalNews(
            contract.conId,
            '',  # all providers
            start,
            end,
            100  # max articles
        )

        # reqHistoricalNews returns None when the account has no news-feed
        # subscription (or nothing in the window). Iterating None raised
        # "'NoneType' object is not iterable" once per instrument — treat it as
        # simply "no news" instead of an error.
        if not news_articles:
            print(f"    – no IBKR news (no subscription or none in range)")
            return result

        for article in news_articles:
            # Fetch full article text
            article_data = ib.reqNewsArticle(
                article.providerCode,
                article.articleId,
                []
            )
            
            # Store in news table
            new_id = store.add_news(
                db,
                company,
                article.providerCode,
                f"ibkr://{article.articleId}",
                article.headline,
                datetime.fromtimestamp(article.time).date().isoformat(),
                article_data.articleText if article_data else article.headline
            )
            
            if new_id:
                result["new"] += 1
            
            time.sleep(0.5)  # Rate limit
        
        print(f"    ✓ Fetched {result['new']} new articles")
        
    except Exception as e:
        print(f"    ! Error fetching news: {e}")
        result["errors"] += 1
    
    return result


def scrape_company(ib, db, company, ticker, args):
    """Scrape all IBKR data for one company."""
    print(f"\n{company} ({ticker})")
    
    result = {"fundamentals": 0, "prices": 0, "estimates": 0, "news": 0, "errors": 0, "fallbacks": 0}

    if args.fundamentals_only or not (args.prices_only or args.news_only or args.estimates_only):
        r = fetch_fundamentals(ib, db, company, ticker)
        result["fundamentals"] = r.get("new", 0)
        result["errors"] += r.get("errors", 0)
    
    if args.prices_only or not (args.fundamentals_only or args.news_only or args.estimates_only):
        years = getattr(args, 'years', 5)  # Default to 5 years
        r = fetch_prices(ib, db, company, ticker, years=years)
        result["prices"] = r.get("new", 0)
        result["errors"] += r.get("errors", 0)
        result["fallbacks"] += r.get("fallbacks", 0)
    
    if args.estimates_only or not (args.fundamentals_only or args.prices_only or args.news_only):
        r = fetch_analyst_estimates(ib, db, company, ticker)
        result["estimates"] = r.get("new", 0)
        result["errors"] += r.get("errors", 0)
    
    if args.news_only or not (args.fundamentals_only or args.prices_only or args.estimates_only):
        r = fetch_ibkr_news(ib, db, company, ticker)
        result["news"] = r.get("new", 0)
        result["errors"] += r.get("errors", 0)
    
    return result


def main():
    ap = argparse.ArgumentParser(description="IBKR data scraper")
    ap.add_argument("--db", default=store.DB_PATH)
    ap.add_argument("--company", help="Scrape single company")
    ap.add_argument("--years", type=int, default=5, help="Years of price history (default: 5)")
    ap.add_argument("--fundamentals-only", action="store_true")
    ap.add_argument("--prices-only", action="store_true")
    ap.add_argument("--estimates-only", action="store_true")
    ap.add_argument("--news-only", action="store_true")
    args = ap.parse_args()
    
    print("IBKR Data Scraper")
    print("=" * 60)
    
    # Connect to IBKR
    ib = connect_ibkr()
    
    # Connect to database
    db = store.get_db(args.db)
    
    # Get tradable instruments with tickers. Exclude the 'account' class: it's a
    # pseudo-instrument (ticker 'PORTFOLIO') holding IBKR account-level summary
    # metrics, not a security — IBKR has no contract for it, so skip it here.
    companies = db.execute("""
        SELECT name, ticker
        FROM companies
        WHERE ticker IS NOT NULL AND ticker != ''
          AND asset_class <> 'account'
        ORDER BY name
    """).fetchall()
    
    if args.company:
        companies = [c for c in companies if c[0] == args.company]
        if not companies:
            print(f"Company '{args.company}' not found or has no ticker")
            sys.exit(1)
    
    print(f"\nCollecting data for {len(companies)} companies...\n")
    
    totals = {"fundamentals": 0, "prices": 0, "estimates": 0, "news": 0, "errors": 0, "fallbacks": 0}
    
    for company, ticker in companies:
        try:
            result = scrape_company(ib, db, company, ticker, args)
            for key in totals:
                totals[key] += result.get(key, 0)
        except Exception as e:
            print(f"  ! Error processing {company}: {e}")
            totals["errors"] += 1
    
    ib.disconnect()
    
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Fundamentals: {totals['fundamentals']} metrics")
    print(f"  Prices:       {totals['prices']} data points")
    print(f"  Estimates:    {totals['estimates']} reports")
    print(f"  News:         {totals['news']} articles")
    print(f"  Errors:       {totals['errors']}")
    if totals['fallbacks']:
        print(f"  Yahoo fallbacks: {totals['fallbacks']} instrument(s) — IBKR "
              f"couldn't qualify the symbol (check for a renamed/bad ticker)")


if __name__ == '__main__':
    main()
