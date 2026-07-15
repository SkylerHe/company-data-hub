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


def get_contract(ib, ticker):
    """Create and qualify a stock contract."""
    stock = Stock(ticker, 'SMART', 'USD')
    contracts = ib.qualifyContracts(stock)
    if not contracts:
        print(f"  ! Could not qualify contract for {ticker}")
        return None
    return contracts[0]


def fetch_fundamentals(ib, db, company, ticker):
    """Fetch fundamental data and store in metrics table."""
    print(f"  Fetching fundamentals for {company} ({ticker})...")
    
    contract = get_contract(ib, ticker)
    if not contract:
        return {"errors": 1}
    
    result = {"new": 0, "errors": 0}
    
    try:
        # Get financial summary (ratios, margins, etc.)
        summary_xml = ib.reqFundamentalData(contract, 'ReportsFinSummary')
        time.sleep(1)  # Rate limit
        
        # Get financial statements
        statements_xml = ib.reqFundamentalData(contract, 'ReportsFinStatements')
        time.sleep(1)
        
        # Parse and store (simplified - you'd parse XML properly)
        # For now, just store raw XML in a metric
        period = datetime.now().strftime('%Y-Q%d')
        
        store.add_metric(db, company, 'financial_summary', period, 0, 'xml', 'IBKR', summary_xml)
        store.add_metric(db, company, 'financial_statements', period, 0, 'xml', 'IBKR', statements_xml)
        result["new"] += 2
        
        print(f"    ✓ Stored fundamental data")
        
    except Exception as e:
        print(f"    ! Error fetching fundamentals: {e}")
        result["errors"] += 1
    
    return result


def fetch_prices(ib, db, company, ticker, years=5):
    """Fetch historical daily prices (default: 5 years)."""
    print(f"  Fetching prices for {company} ({ticker}) - last {years} years...")

    contract = get_contract(ib, ticker)
    if not contract:
        return {"errors": 1}

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
        
    except Exception as e:
        print(f"    ! Error fetching prices: {e}")
        result["errors"] += 1
    
    return result


def fetch_analyst_estimates(ib, db, company, ticker):
    """Fetch analyst estimates (EPS, revenue forecasts)."""
    print(f"  Fetching analyst estimates for {company} ({ticker})...")
    
    contract = get_contract(ib, ticker)
    if not contract:
        return {"errors": 1}
    
    result = {"new": 0, "errors": 0}
    
    try:
        # Get analyst estimates
        estimates_xml = ib.reqFundamentalData(contract, 'CalendarReport')
        time.sleep(1)
        
        # Store raw XML (you'd parse this properly in production)
        period = datetime.now().strftime('%Y-%m-%d')
        store.add_metric(db, company, 'analyst_estimates', period, 0, 'xml', 'IBKR', estimates_xml)
        result["new"] += 1
        
        print(f"    ✓ Stored analyst estimates")
        
    except Exception as e:
        print(f"    ! Error fetching estimates: {e}")
        result["errors"] += 1
    
    return result


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
    
    result = {"fundamentals": 0, "prices": 0, "estimates": 0, "news": 0, "errors": 0}
    
    if args.fundamentals_only or not (args.prices_only or args.news_only or args.estimates_only):
        r = fetch_fundamentals(ib, db, company, ticker)
        result["fundamentals"] = r.get("new", 0)
        result["errors"] += r.get("errors", 0)
    
    if args.prices_only or not (args.fundamentals_only or args.news_only or args.estimates_only):
        years = getattr(args, 'years', 5)  # Default to 5 years
        r = fetch_prices(ib, db, company, ticker, years=years)
        result["prices"] = r.get("new", 0)
        result["errors"] += r.get("errors", 0)
    
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
    
    # Get companies with tickers
    companies = db.execute("""
        SELECT name, ticker 
        FROM companies 
        WHERE ticker IS NOT NULL AND ticker != ''
        ORDER BY name
    """).fetchall()
    
    if args.company:
        companies = [c for c in companies if c[0] == args.company]
        if not companies:
            print(f"Company '{args.company}' not found or has no ticker")
            sys.exit(1)
    
    print(f"\nCollecting data for {len(companies)} companies...\n")
    
    totals = {"fundamentals": 0, "prices": 0, "estimates": 0, "news": 0, "errors": 0}
    
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


if __name__ == '__main__':
    main()
