---
name: company-data
description: >-
  Refresh (or add) all data for a single company in the company-data-hub
  finance.db — prices, Yahoo fundamentals, multi-year SEC/EDGAR financial
  statements, SEC filings, and news. Use this before analyzing a company
  (read-fundamentals / value-company) whenever its data may be stale or the
  company isn't tracked yet. Trigger on requests like "refresh MSFT", "pull the
  latest data for Nvidia", "add Palantir to the hub", or "update <ticker> before
  we value it".
---

# Company Data — refresh one company

This skill is a thin orchestrator over the repo's existing collectors plus the
multi-year statements collector. It brings **one** company's data up to date so
the analysis skills have something current to work with. It does not analyze —
that's `read-fundamentals` and `value-company`.

## Prerequisites
- Run from the repo root `~/company-data-hub` with its virtualenv:
  `source venv/bin/activate` (all scrapers assume it).
- `SEC_IDENTITY` must be set in `.env` (already is) — EDGAR requires it.
- The DB is a live ~740 MB file. Every collector here is **additive and
  idempotent** (upserts keyed by company+metric+period or company+url), so
  re-running is always safe and never duplicates.

## Steps

### 1. Resolve the company to its tracked name
Collectors key on the instrument **name**, not the ticker. Resolve first:
```bash
sqlite3 finance.db "SELECT name, ticker, asset_class FROM instruments
  WHERE name LIKE '%<query>%' OR ticker = '<TICKER>';"
```
Use the returned `name` in every command below. If nothing matches, go to step 2.

### 2. (Only if not tracked yet) add the company
```bash
python -c "import store; db=store.get_db(); \
  store.upsert_company(db, name='<Name>', ticker='<TICKER>', sector='<Sector>'); \
  print('added', '<Name>')"
```
Optionally tag industries so `map-industry` picks it up:
```bash
python -c "import store; db=store.get_db(); \
  store.link_company_industry(db, '<Name>', '<Industry>')"
```

### 3. Refresh the sources (skip any the user doesn't need)
```bash
# Snapshot fundamentals (P/E, ROE, margins, beta, shares) — Yahoo
python scrape_yahoo.py --company "<Name>"

# Recent daily prices — Yahoo (use a longer --period for a first backfill)
python scrape_yahoo.py --company "<Name>" --prices --period 1mo

# Multi-year financial statements (revenue, net income, FCF, assets…) — SEC/EDGAR
# THIS is the collector that feeds DCF + trend analysis. US filers only;
# foreign/ADR names have no 10-K and are skipped cleanly.
python scrape_edgar_financials.py --company "<Name>"

# SEC filing documents (10-K/10-Q/8-K text) — optional, for deep reading
python scrape_filings.py --company "<Name>"

# News — optional
python scrape_news.py --company "<Name>"
```
For a US-listed stock you're about to value, the two that matter most are
**`scrape_yahoo.py`** (current price + market data) and
**`scrape_edgar_financials.py`** (the statement history). Run at least those.

Tip: preview EDGAR with `--dry-run` first if you want to see what it will write
without touching the DB.

### 4. Verify what landed
```bash
# Multi-year statement series now present (should show one row per fiscal year)
sqlite3 -header -column finance.db "
SELECT period, round(value/1e9,1) AS value_B, source
FROM metrics m JOIN instruments i ON i.id=m.company_id
WHERE i.ticker='<TICKER>' AND metric='revenue' ORDER BY source, period;"

# Latest price on file
sqlite3 finance.db "SELECT MAX(date) FROM prices p
  JOIN instruments i ON i.id=p.instrument_id WHERE i.ticker='<TICKER>';"
```
Report to the user: how many fiscal years of EDGAR statements are now stored,
the newest price date, and whether fundamentals refreshed. Flag any collector
that returned 0 rows (e.g. a foreign ADR with no 10-K → no EDGAR history; note
it can't be DCF-valued from filings).

## Notes
- **US-listed only** for EDGAR statements — matches the current scope. A name
  with a ticker but no 10-K (ADR/foreign) will simply skip that step.
- Fundamentals change only quarterly; don't re-pull Yahoo more than ~bi-weekly
  (per `.claude/instructions.md`). Prices and EDGAR are cheap to refresh.
- After this, hand off to `read-fundamentals` (health/quality) or `value-company`
  (valuation + buy verdict).
