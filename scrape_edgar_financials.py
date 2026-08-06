#!/usr/bin/env python3
"""
scrape_edgar_financials.py — multi-year financial statements from SEC EDGAR.

The gap this fills: every other source in this repo stores a *single snapshot*
(Yahoo fundamentals are all dated one day; filings hold raw text). Nothing stored
the actual multi-year statement *numbers* — revenue, net income, free cash flow,
assets, etc. across fiscal years. A DCF forecast and any trend-based fundamental
analysis need that history. This collector supplies it.

Per company, it:
  1. Pulls the last N annual reports via edgartools — a 10-K for US filers, or a
     20-F for foreign private issuers (ADRs / NY-registry shares like ASML), which
     file 20-F instead of 10-K. Note: foreign filers often report in their home
     currency (ASML in EUR), so those line items are NOT USD despite the unit tag.
  2. Reads each filing's standardized financial metrics (cross-company-consistent
     line items from XBRL — see edgartools' get_financial_metrics()).
  3. Writes each line item to the metrics table as one row per fiscal year,
     tagged source='SEC/EDGAR' and period='FY2024', so it sits *beside* the Yahoo
     snapshots (period '2026-07-01') and never overwrites them.

Idempotent: store.add_metric upserts on (company, metric, period), so re-runs and
backfills never duplicate. Resilient: a bad ticker or unparseable filing never
aborts the run.

    python scrape_edgar_financials.py                 # all US-listed stocks
    python scrape_edgar_financials.py --company Microsoft
    python scrape_edgar_financials.py --test          # first 5 stocks
    python scrape_edgar_financials.py --years 3        # shallower history
    python scrape_edgar_financials.py --dry-run        # fetch + parse, write nothing

Requires SEC_IDENTITY in .env ("Your Name you@email.com"), same as scrape_filings.py.
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

from edgar import Company, set_identity

try:
    import yfinance as yf
except ImportError:
    yf = None

import store

SOURCE = "SEC/EDGAR"

# EDGAR's ticker→CIK map lags corporate ticker changes; map our stored ticker to
# the symbol EDGAR still indexes (e.g. Fiserv renamed FISV→FI in 2023, but
# edgartools resolves it only as FISV). The stored ticker stays as-is.
EDGAR_TICKER_MAP = {
    "FI": "FISV",   # Fiserv
}

# edgartools' standardized metric key  ->  (our metric name, unit).
# We store raw statement line items only; ratios/EPS are derived later in
# analyze.py so there's one place that owns the math.
METRIC_MAP = {
    "revenue":                    ("revenue",              "USD"),
    "operating_income":           ("operating_income",     "USD"),
    "net_income":                 ("net_income",           "USD"),
    "total_assets":               ("total_assets",         "USD"),
    "total_liabilities":          ("total_liabilities",    "USD"),
    "stockholders_equity":        ("total_equity",         "USD"),
    "current_assets":             ("current_assets",       "USD"),
    "current_liabilities":        ("current_liabilities",  "USD"),
    "operating_cash_flow":        ("operating_cash_flow",  "USD"),
    "capital_expenditures":       ("capital_expenditures", "USD"),
    "free_cash_flow":             ("free_cash_flow",       "USD"),
    "shares_outstanding_basic":   ("shares_basic",         "count"),
    "shares_outstanding_diluted": ("shares_diluted",       "count"),
}


# ----------------------------------------------------------------------------
# Config (same pattern as scrape_filings.py)
# ----------------------------------------------------------------------------
def load_env():
    """Load KEY=VALUE lines from a local .env into os.environ."""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value.strip().strip('"').strip("'")


def setup_sec_identity():
    """Configure the SEC User-Agent identity (required by the EDGAR API)."""
    identity = os.getenv("SEC_IDENTITY", "CompanyDataHub research@example.com")
    set_identity(identity)
    return identity


# ----------------------------------------------------------------------------
# Company selection
# ----------------------------------------------------------------------------
def stock_universe(db, only=None, limit=None):
    """(name, ticker) for US-listed stocks with a ticker. `only` limits to one
    company by name; `limit` caps the count (used by --test)."""
    sql = (
        "SELECT name, ticker FROM instruments "
        "WHERE asset_class = 'stock' AND ticker IS NOT NULL AND ticker <> ''"
    )
    params = []
    if only:
        sql += " AND name = ?"
        params.append(only)
    sql += " ORDER BY name"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return db.execute(sql, params).fetchall()


def fiscal_period(filing) -> str | None:
    """'FY2024' from a filing's period_of_report ('2024-06-30')."""
    por = getattr(filing, "period_of_report", None)
    if not por:
        return None
    year = str(por)[:4]
    return f"FY{year}" if year.isdigit() else None


# ----------------------------------------------------------------------------
# Currency (foreign filers report in their home currency — convert to USD)
# ----------------------------------------------------------------------------
_FX_CACHE = {}


# Raw XBRL concepts to backfill when edgartools' standardizer misses a metric on
# a foreign (IFRS) filer — e.g. TSMC files under ifrs-full:, so its capex and
# total assets never map. Names are namespace-qualified (by_concept needs it) and
# tried in priority order: us-gaap first, then the IFRS equivalents. FCF is then
# derived as OCF − capex.
_XBRL_FALLBACK_CONCEPTS = {
    "capital_expenditures": [
        "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
        "us-gaap:PaymentsToAcquireProductiveAssets",
        "ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",  # TSMC
        "ifrs-full:PurchaseOfPropertyPlantAndEquipmentIntangibleAssetsAndOtherAssets",
    ],
    "total_assets": ["us-gaap:Assets", "ifrs-full:Assets"],
    # Weighted-average share counts. edgartools' standardizer misses these on some
    # filers (banks like Capital One), which also breaks the basic-vs-diluted
    # dilution check. These are counts (XBRL unit 'shares'), not a currency.
    "shares_outstanding_basic": [
        "us-gaap:WeightedAverageNumberOfSharesOutstandingBasic",
        "ifrs-full:WeightedAverageShares",
    ],
    "shares_outstanding_diluted": [
        "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding",
        "ifrs-full:AdjustedWeightedAverageShares",
    ],
}


def _missing(v):
    """A metric that needs backfilling: absent, non-numeric, or a bogus zero
    (edgartools returns 0.0 for tags it can't map, e.g. TSMC's total_assets)."""
    return not isinstance(v, (int, float)) or v == 0


def load_companyfacts(cik, identity):
    """Fetch a filer's full SEC XBRL companyfacts once. Returns the dict or None."""
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": identity})
        return json.load(urllib.request.urlopen(req, timeout=25))
    except Exception:
        return None


def currency_from_facts(facts):
    """Reporting currency from companyfacts (e.g. ASML → EUR, TSMC → TWD).

    Reads the ISO unit the balance-sheet totals are denominated in. Defaults to
    'USD' — US filers report in USD anyway."""
    if not facts:
        return "USD"
    for taxo in facts.get("facts", {}).values():
        for concept in ("Assets", "Liabilities", "StockholdersEquity"):
            fact = taxo.get(concept)
            if not fact:
                continue
            for unit in fact.get("units", {}):
                if len(unit) == 3 and unit.isalpha():  # ISO currency code
                    return unit
    return "USD"


def filing_xbrl_value(xbrl, concept_names, year, unit_ref):
    """Pull one annual value for a concept from a filing's OWN XBRL — unlike the
    aggregated companyfacts API, this is never SEC-lagged, so it has the newest
    fiscal year too. Filtered to `unit_ref` (the reporting currency for monetary
    values, or 'shares' for share counts), non-dimensioned, and the fiscal year
    (duration facts date on period_end, instant/balance-sheet facts on
    period_instant). Tries concept_names in priority order. Returns float or None.

    NOTE: each concept needs a FRESH query — the query builder chains filters, so
    reusing one object would AND the concepts together and match nothing."""
    if xbrl is None or year is None:
        return None
    want, ystr = unit_ref.lower(), str(year)
    for name in concept_names:
        try:
            df = xbrl.facts.query().by_concept(name).to_dataframe()
        except Exception:
            continue
        if df is None or len(df) == 0:
            continue
        for _, r in df.iterrows():
            if str(r.get("unit_ref", "")).lower() != want:
                continue
            if r.get("is_dimensioned"):
                continue
            date = ""
            for col in ("period_end", "period_instant"):
                d = r.get(col)
                if d is not None and str(d) not in ("nan", "NaT", ""):
                    date = str(d)
                    break
            if not date.startswith(ystr):
                continue
            v = r.get("numeric_value")
            if v is None:
                v = r.get("value")
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def usd_fx_rate(currency):
    """Current spot rate to convert `currency` → USD (1.0 for USD, None if no data).

    We apply this one current rate to every fiscal year. That keeps growth rates
    (and thus the DCF's CAGR / reverse-DCF) exact — a constant multiplier doesn't
    change a CAGR — and makes the latest year, which the DCF projects from, correct.
    Per-year average rates would only refine the historical absolute levels."""
    if currency == "USD":
        return 1.0
    if currency in _FX_CACHE:
        return _FX_CACHE[currency]
    rate = None
    if yf is not None:
        try:
            hist = yf.Ticker(f"{currency}USD=X").history(period="5d")
            if hist is not None and not hist.empty:
                rate = float(hist["Close"].iloc[-1])
        except Exception:
            rate = None
    _FX_CACHE[currency] = rate
    return rate


# ----------------------------------------------------------------------------
# Core
# ----------------------------------------------------------------------------
def _latest_annual_filings(company_obj, form, years):
    """Fetch the latest N annual filings of one form, normalized to a plain list.

    .latest(N) returns an EntityFilings collection, but with only one filing
    available (recent IPOs like CRWV) it returns a single, NON-iterable
    EntityFiling. Normalize all three shapes (None / single / iterable) to a list.
    Returns [] on no match or lookup error.
    """
    try:
        filings = company_obj.get_filings(form=form).latest(years)
    except Exception:
        return []
    if filings is None:
        return []
    if isinstance(filings, list):
        return filings
    try:
        return list(filings)
    except TypeError:
        return [filings]  # single EntityFiling


def scrape_company_financials(db, company, ticker, args) -> dict:
    """Pull the last N annual reports for one company and store their line items.

    US filers file a 10-K; foreign private issuers (ADRs / NY-registry shares like
    ASML) file a 20-F instead. Try 10-K first, then fall back to 20-F so foreign
    names get fundamentals too. edgartools parses both identically via XBRL.
    Returns a small summary dict for reporting."""
    result = {"filings": 0, "written": 0, "errors": 0}

    symbol = EDGAR_TICKER_MAP.get(ticker, ticker)
    cik = getattr(args, "cik", None)
    try:
        # A delisted/renamed ticker (e.g. Discover 'DFS' after Capital One acquired it)
        # no longer maps to a CIK — pass --cik to resolve it directly.
        company_obj = Company(int(cik)) if cik else Company(symbol)
    except Exception as e:
        alias = f" (as CIK {cik})" if cik else (f" (as {symbol})" if symbol != ticker else "")
        print(f"    ! EDGAR lookup failed for {ticker}{alias}: {e}")
        result["errors"] += 1
        return result

    filings = _latest_annual_filings(company_obj, "10-K", args.years)
    form_used = "10-K"
    if not filings:
        # No 10-K — try the foreign-filer annual report.
        filings = _latest_annual_filings(company_obj, "20-F", args.years)
        form_used = "20-F"
    if not filings:
        print("    · no 10-K or 20-F filings found")
        return result
    if form_used == "20-F":
        print(f"    · foreign filer — using 20-F ({len(filings)} found)")

    # Foreign filers report in their home currency (ASML → EUR); convert monetary
    # line items to USD so downstream valuation isn't mixing currencies against a
    # USD price. Share counts stay as-is. We also reuse companyfacts to backfill
    # metrics edgartools' standardizer misses on IFRS filers (TSMC's capex etc.).
    facts = load_companyfacts(company_obj.cik, os.environ.get("SEC_IDENTITY", ""))
    currency = currency_from_facts(facts)
    fx = usd_fx_rate(currency)
    if currency != "USD":
        if fx:
            print(f"    · reports in {currency} — converting → USD @ {fx:.4f} (current spot)")
        else:
            print(f"    · reports in {currency} — FX unavailable; storing native {currency}")

    for filing in filings:
        period = fiscal_period(filing)
        if not period:
            continue
        try:
            metrics = filing.obj().financials.get_financial_metrics()
        except Exception as e:
            print(f"    ! {period}: could not parse financials ({type(e).__name__})")
            result["errors"] += 1
            continue

        # Backfill tags edgartools missed (IFRS filers) from the filing's own XBRL,
        # in native currency so the conversion step below treats them like every
        # other line. Only touch the filing's XBRL if something's actually missing
        # (US filers rarely are). Then derive FCF = OCF − capex if still missing.
        year = int(period[2:]) if period[2:].isdigit() else None
        need = [k for k in _XBRL_FALLBACK_CONCEPTS if _missing(metrics.get(k))]
        if need and year:
            try:
                fx_xbrl = filing.xbrl()
            except Exception:
                fx_xbrl = None
            for std_key in need:
                # monetary metrics filter on the reporting currency; share counts
                # on the 'shares' XBRL unit (they carry no currency).
                is_count = METRIC_MAP.get(std_key, (None, ""))[1] == "count"
                target = "shares" if is_count else currency
                v = filing_xbrl_value(fx_xbrl, _XBRL_FALLBACK_CONCEPTS[std_key], year, target)
                if v is not None:
                    metrics[std_key] = v
        if _missing(metrics.get("free_cash_flow")):
            ocf, capex = metrics.get("operating_cash_flow"), metrics.get("capital_expenditures")
            if not _missing(ocf) and not _missing(capex):
                metrics["free_cash_flow"] = ocf - abs(capex)

        result["filings"] += 1
        for key, (metric_name, unit) in METRIC_MAP.items():
            value = metrics.get(key)
            if value is None or not isinstance(value, (int, float)):
                continue
            out_value, out_unit = float(value), unit
            # Convert monetary line items (unit 'USD') from the home currency;
            # leave share counts (unit 'count') alone. If FX is unavailable, store
            # the native value with a truthful currency tag rather than mislabel it.
            if unit == "USD" and currency != "USD":
                if fx:
                    out_value *= fx
                else:
                    out_unit = currency
            if args.dry_run:
                result["written"] += 1
                continue
            try:
                store.add_metric(db, company, metric_name, period,
                                  out_value, unit=out_unit, source=SOURCE)
                result["written"] += 1
            except Exception as e:
                print(f"    ! store error ({metric_name} {period}): {e}")
                result["errors"] += 1

    return result


def main():
    ap = argparse.ArgumentParser(description="Multi-year SEC EDGAR financials")
    ap.add_argument("--db", default=store.DB_PATH, help="SQLite path")
    ap.add_argument("--company", help="limit to one company (by name)")
    ap.add_argument("--cik", help="resolve EDGAR by this CIK directly (for a delisted/"
                                  "renamed ticker edgartools can't map, e.g. acquired DFS)")
    ap.add_argument("--test", action="store_true", help="first 5 stocks only")
    ap.add_argument("--years", type=int, default=5,
                    help="how many annual 10-Ks to pull (default 5)")
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch and parse but write nothing")
    args = ap.parse_args()

    load_env()
    identity = setup_sec_identity()

    db = store.get_db(args.db)
    store.init_db(db)  # safe no-op if it already exists

    universe = stock_universe(
        db, only=args.company, limit=5 if args.test else None
    )
    if args.company and not universe:
        print(f"'{args.company}' is not a US-listed stock in {args.db}", file=sys.stderr)
        sys.exit(1)

    print(f"EDGAR financials · {len(universe)} company(ies) · last {args.years} FY "
          f"{'(dry run) ' if args.dry_run else ''}· identity: {identity}\n")

    totals = {"filings": 0, "written": 0, "errors": 0}
    for name, ticker in universe:
        print(f"  {name} ({ticker})")
        # Per-company isolation: no single unparseable filing can abort the batch.
        try:
            r = scrape_company_financials(db, name, ticker, args)
        except Exception as e:
            print(f"    ! unexpected error, skipping: {type(e).__name__}: {e}")
            totals["errors"] += 1
            continue
        print(f"    filings={r['filings']} written={r['written']} errors={r['errors']}")
        for k in totals:
            totals[k] += r[k]

    print(f"\nDone. filings={totals['filings']} rows_written={totals['written']} "
          f"errors={totals['errors']}")
    db.close()


if __name__ == "__main__":
    main()
