#!/usr/bin/env python3
"""
scrape_yahoo.py - Collect fundamental data from Yahoo Finance

Collects:
1. Valuation ratios (P/E, P/B, EV/EBITDA, PEG)
2. Profitability metrics (margins, ROE, ROA)
3. Growth metrics (revenue growth, earnings growth)
4. Financial health (debt/equity, current ratio)
5. Per-share metrics (EPS, book value, free cash flow)
6. Company info (market cap, shares outstanding)
7. Earnings dates (next earnings call)

Requirements:
- pip install yfinance

Usage:
    python scrape_yahoo.py                    # collect all companies
    python scrape_yahoo.py --company NVIDIA   # single company
    python scrape_yahoo.py --test            # test with 5 companies
"""

import argparse
import sys
import time
from datetime import datetime

try:
    import yfinance as yf
except ImportError:
    print("Error: yfinance not installed")
    print("Install with: pip install yfinance")
    sys.exit(1)

import store


# Metrics to collect from Yahoo Finance
# Maps: (Yahoo key, our metric name, unit)
VALUATION_METRICS = [
    ('trailingPE', 'pe_ratio', 'ratio'),
    ('forwardPE', 'forward_pe', 'ratio'),
    ('priceToBook', 'pb_ratio', 'ratio'),
    ('priceToSalesTrailing12Months', 'ps_ratio', 'ratio'),
    ('enterpriseToEbitda', 'ev_ebitda', 'ratio'),
    ('pegRatio', 'peg_ratio', 'ratio'),
    ('marketCap', 'market_cap', 'USD'),
]

PROFITABILITY_METRICS = [
    ('profitMargins', 'profit_margin', '%'),
    ('grossMargins', 'gross_margin', '%'),
    ('operatingMargins', 'operating_margin', '%'),
    ('returnOnEquity', 'roe', '%'),
    ('returnOnAssets', 'roa', '%'),
]

GROWTH_METRICS = [
    ('revenueGrowth', 'revenue_growth', '%'),
    ('earningsGrowth', 'earnings_growth', '%'),
    ('earningsQuarterlyGrowth', 'earnings_growth_qoq', '%'),
]

FINANCIAL_HEALTH_METRICS = [
    ('debtToEquity', 'debt_to_equity', 'ratio'),
    ('currentRatio', 'current_ratio', 'ratio'),
    ('quickRatio', 'quick_ratio', 'ratio'),
]

PER_SHARE_METRICS = [
    ('trailingEps', 'eps_ttm', 'USD'),
    ('forwardEps', 'eps_forward', 'USD'),
    ('bookValue', 'book_value_per_share', 'USD'),
    ('freeCashflow', 'free_cashflow', 'USD'),
]

FUNDAMENTAL_DATA = [
    ('totalRevenue', 'revenue', 'USD'),
    ('totalCash', 'cash', 'USD'),
    ('totalDebt', 'total_debt', 'USD'),
    ('totalAssets', 'total_assets', 'USD'),
    ('sharesOutstanding', 'shares_outstanding', 'shares'),
    ('dividendYield', 'dividend_yield', '%'),
    ('beta', 'beta', 'ratio'),
]

ALL_METRICS = (
    VALUATION_METRICS +
    PROFITABILITY_METRICS +
    GROWTH_METRICS +
    FINANCIAL_HEALTH_METRICS +
    PER_SHARE_METRICS +
    FUNDAMENTAL_DATA
)


def _num(v):
    """Coerce a yfinance cell to a float, or None (also maps NaN -> None)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f  # f != f is True only for NaN


def fetch_yahoo_prices(db, company, ticker, period="5d"):
    """Fetch recent daily OHLCV from Yahoo and upsert into the wide `prices` table.

    This is the daily-price FALLBACK for when IBKR / IB Gateway is unavailable. A
    short look-back (default 5 trading days) fills any recent gap cheaply rather than
    pulling years of history. Rows are written with source='Yahoo'; because
    store.add_price upserts on (instrument, date), a later IBKR run for the same day
    simply overwrites them once the gateway is back."""
    print(f"  Fetching Yahoo prices for {company} ({ticker}) [{period}]...")

    result = {"new": 0, "errors": 0}

    try:
        hist = yf.Ticker(ticker).history(period=period)
        if hist is None or hist.empty:
            print("    ! No price data returned")
            return result

        for idx, row in hist.iterrows():
            date = idx.strftime('%Y-%m-%d')
            store.add_price(
                db, company, date,
                open=_num(row.get('Open')),
                high=_num(row.get('High')),
                low=_num(row.get('Low')),
                close=_num(row.get('Close')),
                volume=_num(row.get('Volume')),
                source='Yahoo',
            )
            result["new"] += 1

        print(f"    ✓ Stored {result['new']} days of price data")
        if result["new"]:
            store.recompute_moving_averages(db, company)  # refresh 20/50/200-day SMAs

    except Exception as e:
        print(f"    ! Error fetching prices: {e}")
        result["errors"] += 1

    return result


def fetch_yahoo_fundamentals(db, company, ticker):
    """Fetch all fundamental data from Yahoo Finance."""
    print(f"  Fetching Yahoo Finance data for {company} ({ticker})...")

    result = {"new": 0, "errors": 0}

    try:
        # Get ticker data
        stock = yf.Ticker(ticker)
        info = stock.info

        # Use today's date as the period
        period = datetime.now().strftime('%Y-%m-%d')

        # Collect all metrics
        for yahoo_key, metric_name, unit in ALL_METRICS:
            if yahoo_key in info and info[yahoo_key] is not None:
                value = info[yahoo_key]

                # Convert percentages to decimal (Yahoo gives 0.15 for 15%)
                if unit == '%' and value is not None:
                    value = value * 100  # Convert to percentage

                store.add_metric(db, company, metric_name, period, value, unit, 'Yahoo')
                result["new"] += 1

        # Get earnings calendar (next earnings date)
        try:
            calendar = stock.calendar
            if calendar is not None and not calendar.empty:
                # Calendar returns dataframe with 'Earnings Date' or similar
                if 'Earnings Date' in calendar.index:
                    earnings_date = calendar.loc['Earnings Date'].iloc[0]
                    if earnings_date:
                        # Store as text in metrics table
                        date_str = earnings_date.strftime('%Y-%m-%d') if hasattr(earnings_date, 'strftime') else str(earnings_date)
                        store.add_metric(db, company, 'next_earnings_date', period, 0, date_str, 'Yahoo')
                        result["new"] += 1
        except Exception:
            pass  # Earnings date not always available

        print(f"    ✓ Stored {result['new']} metrics")

    except Exception as e:
        print(f"    ! Error fetching data: {e}")
        result["errors"] += 1

    return result


def main():
    ap = argparse.ArgumentParser(description="Yahoo Finance scraper (fundamentals + price fallback)")
    ap.add_argument("--db", default=store.DB_PATH)
    ap.add_argument("--company", help="Scrape single company")
    ap.add_argument("--test", action="store_true", help="Test with 5 companies")
    ap.add_argument("--prices", action="store_true",
                    help="Fetch daily OHLCV into the prices table (IBKR fallback) "
                         "instead of fundamentals")
    ap.add_argument("--period", default="5d",
                    help="Look-back window for --prices (yfinance period, default 5d)")
    args = ap.parse_args()

    mode = "Daily Prices (fallback)" if args.prices else "Fundamentals"
    print(f"Yahoo Finance {mode} Scraper")
    print("=" * 60)

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

    if args.test:
        companies = companies[:5]
        print("\n⚠ TEST MODE: Processing only 5 companies\n")

    noun = "price rows" if args.prices else "fundamentals"
    print(f"\nCollecting {noun} for {len(companies)} companies...\n")

    totals = {"new": 0, "errors": 0}

    for company, ticker in companies:
        try:
            if args.prices:
                result = fetch_yahoo_prices(db, company, ticker, period=args.period)
            else:
                result = fetch_yahoo_fundamentals(db, company, ticker)
            totals["new"] += result.get("new", 0)
            totals["errors"] += result.get("errors", 0)

            # Rate limit - be nice to Yahoo
            time.sleep(0.5)

        except Exception as e:
            print(f"  ! Error processing {company}: {e}")
            totals["errors"] += 1

    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  {'Price rows' if args.prices else 'Metrics'} collected: {totals['new']}")
    print(f"  Errors:            {totals['errors']}")


if __name__ == '__main__':
    main()
