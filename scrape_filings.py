"""
scrape_filings.py — SEC filing scraper for the company finance database.

What it does, per company:
  1. Fetches recent SEC filings (10-K, 10-Q, 8-K) using the edgartools library.
  2. Filters filings newer than the company's `last_fetched` watermark from the
     filings table, so daily runs only process new items.
  3. Extracts full filing text and stores in the filings table.
  4. Advances the watermark to prevent reprocessing.

It is deliberately resilient: a failed filing fetch never aborts the run.
Everything lives in store.py's schema; this file only ingests.

    pip install -r requirements.txt
    python store.py --init                     # once, creates finance.db
    python store.py --load industries.json     # once, loads your industries + companies
    python scrape_filings.py                   # the daily job

Useful flags:
    python scrape_filings.py --company NVIDIA  # only one company
    python scrape_filings.py --dry-run         # fetch + parse, write nothing
    python scrape_filings.py --since 2025-01-01  # override watermark for a backfill
    python scrape_filings.py --db finance.db

Requirements:
  - Set SEC_IDENTITY environment variable: "YourName email@domain.com"
    or it will use a default identity (not recommended for production).
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from edgar import Company, set_identity

import store


# ----------------------------------------------------------------------------
# Load environment variables from .env file
# ----------------------------------------------------------------------------
def load_env():
    """Load environment variables from .env file if it exists."""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value


# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
def setup_sec_identity():
    """Configure SEC User-Agent identity (required by SEC EDGAR API)."""
    identity = os.getenv("SEC_IDENTITY", "CompanyDataHub research@example.com")
    set_identity(identity)
    return identity


# ----------------------------------------------------------------------------
# Parsing helpers
# ----------------------------------------------------------------------------
def parse_iso(s: str) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def get_filing_watermark(db, company: str) -> datetime | None:
    """Get the most recent filing date for this company, used as watermark."""
    cur = db.execute(
        """
        SELECT MAX(date) FROM filings
        WHERE company_id = (SELECT id FROM companies WHERE name = ?)
        """,
        (company,)
    )
    row = cur.fetchone()
    return parse_iso(row[0]) if row and row[0] else None


def set_filing_watermark(db, company: str, timestamp: str):
    """Update the company's last_fetched timestamp."""
    store.set_last_fetched(db, company, timestamp)


# ----------------------------------------------------------------------------
# Core
# ----------------------------------------------------------------------------
def scrape_company_filings(db, company: str, ticker: str, args) -> dict:
    """Scrape SEC filings for one company. Returns summary dict for reporting."""
    result = {"seen": 0, "new": 0, "skipped_old": 0, "errors": 0}

    if not ticker:
        print(f"    ! no ticker available, skipping SEC filings")
        return result

    # Watermark: only consider filings newer than this
    if args.since:
        watermark = parse_iso(args.since)
    else:
        watermark = get_filing_watermark(db, company)

    newest_seen = watermark
    filing_types = ["10-K", "10-Q", "8-K"]

    try:
        # Fetch company filings from SEC EDGAR
        edgar_company = Company(ticker)

        for filing_type in filing_types:
            try:
                # Get recent filings of this type
                filings = edgar_company.get_filings(form=filing_type)
                if filings is None:
                    continue
                filings = filings.latest(20)

                if not filings:
                    continue

                for filing in filings:
                    result["seen"] += 1

                    # Parse filing date
                    filing_date_str = str(filing.filing_date)
                    filing_dt = parse_iso(filing_date_str)

                    # Watermark filter
                    if watermark and filing_dt and filing_dt <= watermark:
                        result["skipped_old"] += 1
                        continue

                    if filing_dt and (newest_seen is None or filing_dt > newest_seen):
                        newest_seen = filing_dt

                    # Extract filing details
                    url = str(filing.homepage) if filing.homepage else f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type={filing_type}"
                    title = f"{filing_type} - {filing_date_str}"

                    # Fetch full filing text
                    content = ""
                    if not args.no_fetch_text:
                        try:
                            content = filing.text()
                        except Exception as e:
                            print(f"    ! text extraction error for {filing_type}: {e}")
                            content = str(filing.html())  # Fallback to HTML

                    if args.dry_run:
                        result["new"] += 1
                        continue

                    # Store filing
                    try:
                        company_id = store.company_id(db, company)
                        db.execute(
                            """
                            INSERT INTO filings
                                (company_id, type, url, date, title, content, fetched_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(company_id, url) DO NOTHING
                            """,
                            (
                                company_id,
                                filing_type,
                                url,
                                filing_date_str,
                                title,
                                content,
                                datetime.now(timezone.utc).isoformat(timespec="seconds")
                            )
                        )
                        if db.execute("SELECT changes()").fetchone()[0] > 0:
                            result["new"] += 1
                        db.commit()
                    except Exception as e:
                        print(f"    ! store error: {e}")
                        result["errors"] += 1

            except Exception as e:
                print(f"    ! filing type {filing_type} error: {e}")
                result["errors"] += 1
                continue

    except Exception as e:
        print(f"    ! company lookup error: {e}")
        result["errors"] += 1
        return result

    # Advance the watermark to the newest filing we saw (or now)
    if not args.dry_run and newest_seen:
        stamp = newest_seen.isoformat(timespec="seconds")
        set_filing_watermark(db, company, stamp)

    return result


def main():
    # Load environment variables from .env file
    load_env()

    ap = argparse.ArgumentParser(description="SEC filing scraper")
    ap.add_argument("--db", default=store.DB_PATH, help="SQLite path")
    ap.add_argument("--company", help="limit to one company (by name)")
    ap.add_argument("--no-fetch-text", action="store_true",
                    help="skip full-text extraction; store HTML only")
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch and parse but write nothing")
    ap.add_argument("--since", help="override watermark, ISO date (e.g. 2025-01-01)")
    args = ap.parse_args()

    # Set up SEC identity
    identity = setup_sec_identity()
    print(f"Using SEC identity: {identity}\n")

    db = store.get_db(args.db)
    store.init_db(db)  # safe; no-op if it already exists

    # Get all public companies (those with tickers)
    cur = db.execute(
        """
        SELECT name, ticker FROM companies
        WHERE ticker IS NOT NULL AND ticker != ''
        ORDER BY name
        """
    )
    companies = {row[0]: row[1] for row in cur.fetchall()}

    if args.company:
        if args.company not in companies:
            print(f"'{args.company}' not found or has no ticker", file=sys.stderr)
            sys.exit(1)
        companies = {args.company: companies[args.company]}

    totals = {"seen": 0, "new": 0, "skipped_old": 0, "errors": 0}
    print(f"Scraping SEC filings for {len(companies)} public company(ies) "
          f"{'(dry run) ' if args.dry_run else ''}\n")

    for company, ticker in companies.items():
        print(f"  {company} ({ticker})")
        r = scrape_company_filings(db, company, ticker, args)
        print(f"    seen={r['seen']} new={r['new']} "
              f"skipped_old={r['skipped_old']} errors={r['errors']}")
        for k in totals:
            totals[k] += r[k]

    print(f"\nDone. new={totals['new']} seen={totals['seen']} "
          f"skipped_old={totals['skipped_old']} errors={totals['errors']}")
    db.close()


if __name__ == "__main__":
    main()
