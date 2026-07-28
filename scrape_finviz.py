#!/usr/bin/env python3
"""Finviz snapshot scraper — a CORRECTION LAYER over the Yahoo snapshot.

Yahoo Finance serves a handful of *structurally corrupt* fundamental fields for
some names (most visibly ASML: bookValue $1.16, enterpriseValue $35T, so the
derived P/B and EV/EBITDA are garbage — see the CLAUDE.md "known bad points"
note). The corruption is in Yahoo's own feed, so re-pulling Yahoo can't fix it.

Finviz reports these same fields correctly. This scraper pulls the small set of
fields Yahoo demonstrably mangles (plus a couple Yahoo doesn't provide at all)
and stores them with source='Finviz'. `analyze.snapshot()` then PREFERS Finviz
over Yahoo, so the analysis engines (industry.py, valuation.py) automatically
read the corrected value while everything else stays on Yahoo.

Scope is deliberately narrow — this is a correction/supplement, not a full
second fundamentals source. Everything else still comes from Yahoo/EDGAR.

Usage (run from repo root, venv active):
    python scrape_finviz.py --company ASML     # one name
    python scrape_finviz.py                     # all tracked tickers
    python scrape_finviz.py --test              # first 5
"""

import argparse
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

import store

# Finviz returns 403 to non-browser agents; present a normal desktop UA.
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# The fields we take from Finviz. Keyed by the exact Finviz snapshot label.
#   (our metric name, unit)
# - book_value_per_share / pb_ratio / ev_ebitda : Yahoo is corrupt here — OVERRIDE.
# - enterprise_value / roic                      : Yahoo doesn't provide these — SUPPLEMENT.
# - peg_ratio                                    : Finviz's growth-based PEG — OVERRIDE.
# Percent fields (ROIC) are stored in percent-form (45.57), matching how
# scrape_yahoo stores roe/roa, so the engines compare like with like.
FINVIZ_METRICS = {
    "Book/sh":          ("book_value_per_share", "USD"),
    "P/B":              ("pb_ratio",             "ratio"),
    "EV/EBITDA":        ("ev_ebitda",            "ratio"),
    "Enterprise Value": ("enterprise_value",     "USD"),
    "ROIC":             ("roic",                 "%"),
    "PEG":              ("peg_ratio",            "ratio"),
}

# One label/value cell pair from the Finviz snapshot table:
#   <div class="snapshot-td-label">Book/sh</div> ... <div class="snapshot-td-content"><b>64.74</b></div>
_CELL_RE = re.compile(
    r'snapshot-td-label"[^>]*>([^<]+)</div>.*?snapshot-td-content"[^>]*>(.*?)</div>',
    re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_SUFFIX = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}


def _parse_number(raw):
    """Parse a Finviz value string into a float, or None if not numeric.

    Handles '64.74', '598.94B', '45.57%', '-5.67%', '1,570.59', and '-' (missing).
    Percent values return the plain number (45.57), NOT a fraction.
    """
    if raw is None:
        return None
    s = raw.strip().replace(",", "")
    if s in ("", "-", "N/A"):
        return None
    s = s.rstrip("%")
    mult = 1.0
    if s and s[-1] in _SUFFIX:
        mult = _SUFFIX[s[-1]]
        s = s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return None


def fetch_finviz_snapshot(ticker):
    """Fetch and parse the Finviz snapshot table. Returns {label: raw_string}."""
    url = f"https://finviz.com/quote.ashx?t={ticker}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8", "ignore")
    cells = {}
    for label, value_html in _CELL_RE.findall(html):
        cells[label.strip()] = _TAG_RE.sub("", value_html).strip()
    return cells


def fetch_finviz_fundamentals(db, company, ticker):
    """Pull the correction-set fields for one company and store them (source=Finviz).

    Distinguishes three outcomes: `new` (fields stored), `skipped` (no Finviz page
    or none of our target fields — benign: OTC ADRs and ETFs/funds), and `errors`
    (unexpected failures worth a human's attention)."""
    print(f"  Fetching Finviz snapshot for {company} ({ticker})...")
    result = {"new": 0, "errors": 0, "skipped": 0}

    try:
        cells = fetch_finviz_snapshot(ticker)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # No Finviz page for this symbol (typically an OTC ADR) — keep Yahoo's value.
            print("    – Not on Finviz (404); leaving Yahoo value in place")
            result["skipped"] += 1
        else:
            print(f"    ! HTTP error fetching Finviz page: {e}")
            result["errors"] += 1
        return result
    except Exception as e:
        print(f"    ! Error fetching Finviz page: {e}")
        result["errors"] += 1
        return result

    if not cells:
        print("    – No snapshot table (not a Finviz-covered security); skipping")
        result["skipped"] += 1
        return result

    period = datetime.now().strftime("%Y-%m-%d")
    stored = []
    for label, (metric, unit) in FINVIZ_METRICS.items():
        value = _parse_number(cells.get(label))
        if value is None:
            continue
        store.add_metric(db, company, metric, period, value, unit, "Finviz")
        result["new"] += 1
        stored.append(f"{metric}={value:g}")

    if stored:
        print(f"    ✓ Stored {result['new']}: {', '.join(stored)}")
    else:
        # Page exists but lacks company fundamentals (e.g. an ETF/fund) — expected.
        print("    – No company fundamentals on page (ETF/fund?); skipping")
        result["skipped"] += 1
    return result


def main():
    ap = argparse.ArgumentParser(
        description="Finviz snapshot scraper (correction layer over Yahoo)")
    ap.add_argument("--db", default=store.DB_PATH)
    ap.add_argument("--company", help="Scrape a single company (by name)")
    ap.add_argument("--test", action="store_true", help="Test with first 5 companies")
    ap.add_argument("--sleep", type=float, default=1.0,
                    help="Seconds to wait between requests (be nice to Finviz)")
    args = ap.parse_args()

    print("Finviz Snapshot Scraper (Yahoo correction layer)")
    print("=" * 60)

    db = store.get_db(args.db)

    # Only stocks/REITs have the fields we correct (Book/sh, P/B, EV/EBITDA, ROIC).
    # ETFs, funds, bonds, commodities, crypto, index and the 'account' pseudo-
    # instrument have no company fundamentals on Finviz, so there's nothing to fix.
    companies = db.execute("""
        SELECT name, ticker
        FROM companies
        WHERE ticker IS NOT NULL AND ticker != ''
          AND asset_class IN ('stock', 'reit')
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

    print(f"\nCorrecting snapshot fields for {len(companies)} companies...\n")

    totals = {"new": 0, "errors": 0, "skipped": 0}
    for company, ticker in companies:
        try:
            r = fetch_finviz_fundamentals(db, company, ticker)
            totals["new"] += r["new"]
            totals["errors"] += r["errors"]
            totals["skipped"] += r["skipped"]
            time.sleep(args.sleep)  # politeness
        except Exception as e:
            print(f"  ! Error processing {company}: {e}")
            totals["errors"] += 1

    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Metrics corrected: {totals['new']}")
    print(f"  Skipped (no Finviz page / not a stock): {totals['skipped']}")
    print(f"  Errors:            {totals['errors']}")


if __name__ == "__main__":
    main()
