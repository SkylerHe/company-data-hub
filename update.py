#!/usr/bin/env python3
"""
update.py - Smart data update script

Runs updates based on what's needed:
- Prices: Daily (when IB Gateway running)
- Fundamentals: Bi-weekly (every 2 weeks)
- Filings: Weekly
- News: Optional (3x per week)

Usage:
    python update.py                    # Smart update (checks what's due)
    python update.py --force-all        # Force update everything
    python update.py --prices-only      # Just update prices
    python update.py --fundamentals     # Just update fundamentals
"""

import argparse
import subprocess
import sys
import os
from datetime import datetime, timedelta, timezone
import sqlite3

DB_PATH = "finance.db"


def _load_dotenv(path=".env"):
    """Load KEY=VALUE lines from a local .env into os.environ (without overriding
    real env vars). Lets the news stage find FINNHUB_API_KEY without an explicit
    export; .env is git-ignored so the key stays out of source control."""
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


def get_last_update(source):
    """Get the last update time for a data source."""
    try:
        db = sqlite3.connect(DB_PATH)
        cursor = db.cursor()

        if source == 'Yahoo':
            # Yahoo writes both fundamentals (metrics) and OHLCV (prices); take the newest.
            cursor.execute("""
                SELECT MAX(fetched_at) FROM (
                    SELECT MAX(fetched_at) AS fetched_at FROM metrics WHERE source = 'Yahoo'
                    UNION ALL
                    SELECT MAX(fetched_at) FROM prices  WHERE source = 'Yahoo'
                )
            """)
        elif source == 'IBKR':
            cursor.execute("""
                SELECT MAX(fetched_at) FROM (
                    SELECT MAX(fetched_at) AS fetched_at FROM metrics WHERE source = 'IBKR'
                    UNION ALL
                    SELECT MAX(fetched_at) FROM prices  WHERE source = 'IBKR'
                )
            """)
        elif source == 'SEC':
            cursor.execute("""
                SELECT MAX(fetched_at)
                FROM filings
            """)
        elif source == 'News':
            cursor.execute("""
                SELECT MAX(fetched_at)
                FROM news
            """)
        else:
            return None

        result = cursor.fetchone()
        db.close()

        if result and result[0]:
            return datetime.fromisoformat(result[0])
        return None
    except Exception:
        return None


def needs_update(source, days):
    """Check if source needs update based on days threshold."""
    last_update = get_last_update(source)

    if last_update is None:
        return True

    # fetched_at is written in UTC (tz-aware); normalize both sides to avoid a
    # naive-vs-aware subtraction error.
    if last_update.tzinfo is None:
        last_update = last_update.replace(tzinfo=timezone.utc)
    days_since = (datetime.now(timezone.utc) - last_update).days
    return days_since >= days


def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}\n")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=False,
            text=True
        )
        print(f"\n✓ Completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Failed with error code {e.returncode}")
        return False
    except Exception as e:
        print(f"\n✗ Failed: {e}")
        return False


def update_prices(results):
    """Daily prices: IBKR primary, Yahoo daily OHLCV as fallback.

    IB Gateway is flaky (degrades/logs out), so if the IBKR pull fails we fetch a
    short window of daily prices from Yahoo instead. store.add_price upserts on
    (instrument, date), so a later successful IBKR run overwrites the Yahoo rows
    once the gateway is back. Keeps the prices table fresh — and the health-check
    prices-freshness alert quiet — even while IB Gateway is down."""
    ibkr_ok = run_command(
        "source venv/bin/activate && python scrape_ibkr.py --prices-only --years 1",
        "Updating IBKR prices (last 1 year)"
    )
    if ibkr_ok:
        results['prices'] = True
        return

    print("\n⚠ IBKR prices failed (IB Gateway down?) — falling back to Yahoo daily prices\n")
    yahoo_ok = run_command(
        "source venv/bin/activate && python scrape_yahoo.py --prices --period 5d",
        "Updating Yahoo daily prices (fallback)"
    )
    # The price step counts as successful as long as the Yahoo fallback filled the
    # gap, so a gateway outage alone no longer fails the run (exit 1). Only a genuine
    # dual-source failure (IBKR AND Yahoo both down) marks prices failed.
    results['prices'] = yahoo_ok


def main():
    ap = argparse.ArgumentParser(description="Smart data update")
    ap.add_argument("--force-all", action="store_true", help="Force update everything")
    ap.add_argument("--prices-only", action="store_true", help="Only update prices")
    ap.add_argument("--fundamentals", action="store_true", help="Only update fundamentals")
    ap.add_argument("--skip-news", action="store_true", help="Skip news updates")
    args = ap.parse_args()

    start_time = datetime.now()
    print(f"\n{'='*60}")
    print(f"SMART DATA UPDATE - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    results = {}

    # Prices only mode
    if args.prices_only:
        update_prices(results)
        print_summary(start_time, results)
        return

    # Fundamentals only mode
    if args.fundamentals:
        results['fundamentals'] = run_command(
            "source venv/bin/activate && python scrape_yahoo.py",
            "Updating Yahoo fundamentals"
        )
        results['finviz'] = run_command(
            "source venv/bin/activate && python scrape_finviz.py",
            "Correcting snapshot fields from Finviz"
        )
        print_summary(start_time, results)
        return

    # Smart mode - check what needs updating
    print("Checking what needs updating...\n")

    # 1. Prices (daily) — IBKR primary, Yahoo fallback if the gateway is down
    if args.force_all or needs_update('IBKR', 1):
        print("📊 Prices are due for update (daily)")
        update_prices(results)
    else:
        print("✓ Prices are up to date (updated < 1 day ago)\n")
        results['prices'] = None

    # 2. Fundamentals (bi-weekly = 14 days)
    if args.force_all or needs_update('Yahoo', 14):
        print("📈 Fundamentals are due for update (bi-weekly)")
        results['fundamentals'] = run_command(
            "source venv/bin/activate && python scrape_yahoo.py",
            "Updating Yahoo fundamentals + earnings dates"
        )
        # Finviz correction layer: runs on the same cadence as fundamentals since
        # it overwrites the fields Yahoo serves corrupt (book value, P/B, EV/EBITDA)
        # in that same snapshot. See scrape_finviz.py / analyze.snapshot().
        results['finviz'] = run_command(
            "source venv/bin/activate && python scrape_finviz.py",
            "Correcting snapshot fields from Finviz"
        )
    else:
        print("✓ Fundamentals are up to date (updated < 14 days ago)\n")
        results['fundamentals'] = None
        results['finviz'] = None

    # 3. Filings (weekly = 7 days)
    if args.force_all or needs_update('SEC', 7):
        print("📄 SEC filings are due for update (weekly)")
        results['filings'] = run_command(
            "source venv/bin/activate && SEC_IDENTITY='CompanyDataHub research@localhost' python scrape_filings.py",
            "Updating SEC filings"
        )
    else:
        print("✓ SEC filings are up to date (updated < 7 days ago)\n")
        results['filings'] = None

    # 4. News (3x per week = 2 days, optional)
    if not args.skip_news:
        # Check if Finnhub API key is set
        if os.environ.get('FINNHUB_API_KEY'):
            if args.force_all or needs_update('News', 2):
                print("📰 News is due for update (3x per week)")
                results['news'] = run_command(
                    "source venv/bin/activate && python scrape_news.py --days 3",
                    "Updating financial news (last 3 days)"
                )
            else:
                print("✓ News is up to date (updated < 2 days ago)\n")
                results['news'] = None
        else:
            print("⚠ Skipping news (FINNHUB_API_KEY not set)\n")
            results['news'] = None
    else:
        results['news'] = None

    print_summary(start_time, results)


def print_summary(start_time, results):
    """Print update summary."""
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds() / 60

    print(f"\n{'='*60}")
    print(f"UPDATE SUMMARY")
    print(f"{'='*60}\n")
    print(f"Started:  {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Finished: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {duration:.1f} minutes\n")

    print("Results:")
    for task, success in results.items():
        if success is None:
            status = "SKIPPED (up to date)"
        elif success:
            status = "✓ SUCCESS"
        else:
            status = "✗ FAILED"
        print(f"  {task.ljust(15)}: {status}")

    print("\nUpdate Schedule:")
    print("  Prices:       Daily")
    print("  Fundamentals: Every 14 days (bi-weekly)")
    print("  Filings:      Every 7 days (weekly)")
    print("  News:         Every 2 days (3x per week)")

    # Exit with error if any task failed
    if any(s == False for s in results.values()):
        sys.exit(1)


if __name__ == '__main__':
    main()
