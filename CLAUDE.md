# CLAUDE.md — company-data-hub

Orientation index for this repo. Behavioral rules (security, testing, cleanup,
update cadence) live in [`.claude/instructions.md`](.claude/instructions.md);
this file is the **map**: what's here, how it fits, how to run it.

## What this is
A personal **financial-data platform + analysis toolkit** for **CFA Level 1
study and IBKR trading practice**. It collects market data on a tracked universe
into one SQLite DB (`finance.db`), then reads, values, and compares those
companies. Started as pure data collection; now also reasons about the data.

## Architecture (data flow)
```
COLLECT                    STORE            ANALYZE (read-only)        USE
scrape_ibkr    prices  ┐                    analyze.py    ───────► read-fundamentals
scrape_yahoo   snapshot├─► store.py ─► finance.db ─► valuation.py+report.py ─► value-company
scrape_edgar   stmts   │                    industry.py   ───────► map-industry
scrape_filings text    │                                          company-data (refresh)
scrape_news    news    ┘
scrape_ibkr_account ─► account summary
        └─ orchestrated daily by update.py + run_daily.sh, watched by health_check.py
```

## Layout (grouped by role — files are flat at repo root)
- **Collection:** `scrape_ibkr.py` (prices), `scrape_yahoo.py` (fundamentals snapshot + fallback prices), `scrape_edgar_financials.py` (multi-year SEC statements), `scrape_filings.py` (10-K/10-Q/8-K text), `scrape_news.py` (news), `scrape_ibkr_account.py` (portfolio/account)
- **Storage:** `store.py` (schema + all DB helpers — the core), `migrate_schema.py` (one-time migration), `industries.json` (industry config), `finance.db` (gitignored, ~740 MB)
- **Analysis (read-only engines):** `analyze.py` (fundamental health), `valuation.py` (intrinsic value: DCF/CAPM/WACC/reverse-DCF/comps/scenarios), `report.py` (editable Excel model), `industry.py` (peer comparison)
- **Skills** (`.claude/skills/`): `company-data`, `read-fundamentals`, `value-company`, `map-industry`
- **Automation:** `update.py` (smart-cadence orchestrator), `run_daily.sh` (launchd entry), `setup_automation.sh` (installs the agent), `health_check.py` (connectivity + freshness + email alerts), `dashboard.py` (local web UI), `.github/workflows/daily-scrape.yml`
- **Learning/journals:** `CFA_TRADING_CURRICULUM.md` (CFA↔trading study track), `LEARNING_LOG.md` (traceable progress), `CFA_PRACTICE_REVIEW.md` (running tracker of official-site practice: misses, terms, weak spots), `PHILOSOPHY.md` (investing principles), `investment/` (long-term "book"), `trade/` (active-trading "book"). CFA Level I *practice questions* are done on the official CFA website; only the review tracker lives in-repo.

## How to run
```bash
source venv/bin/activate            # all scripts assume the venv + repo-root CWD

# Analysis (read-only; name or ticker)
python analyze.py   --company MSFT              # fundamental health
python valuation.py --company MSFT              # intrinsic value + verdict
python report.py    --company MSFT              # → editable .xlsx model
python industry.py  --industry Semiconductors   # peer map (or --company NVIDIA)

# Data
python update.py                    # smart refresh (prices daily, fundamentals 14d, filings 7d, news 2d)
python scrape_edgar_financials.py --company "<Name>"   # backfill statement history
python health_check.py --dry-run    # status of every source (no email)
```

## Data model (`finance.db`)
- **Instrument-centric:** `companies` is a **VIEW** over `instruments` (insert/update via triggers). Asset classes: stock, etf, fund, bond, reit, commodity, crypto, index, cash, plus **`account`** (a pseudo-class).
- **`metrics`** = `(company_id, metric, period, value, unit, source)`. Two sources, kept distinct on purpose:
  - `source='SEC/EDGAR'` → multi-year **statement trend**, `period='FY2024'…` (revenue, net_income, free_cash_flow, total_assets/equity, shares…)
  - `source='Yahoo'` → **current snapshot** of market ratios, `period` a date like `'2026-07-01'` (pe_ratio, roe, gross_margin, beta, market_cap…)
- **`prices`** = OHLCV per `(instrument_id, date)`, `source` IBKR (primary) or Yahoo (fallback).
- **`industries` + `company_industries`** = **23 thematic industries** (~11 names each: Semiconductors, AI Infrastructure, Defense & Space…). **Not GICS.**
- `filings` (full text), `news` (full-text articles).

## Conventions & gotchas
- **Run from repo root** — `store.DB_PATH = "finance.db"` is CWD-relative.
- **Analysis engines are read-only**; collectors upsert idempotently (keyed by company+metric+period or company+url), so re-runs never duplicate.
- **EDGAR series = trend; Yahoo snapshot = current.** Keep them separate; don't mix a snapshot value into a trend.
- **Foreign/ADR names** (TSM, ASML, ARM…) have no US 10-K → no EDGAR fundamentals (show `-`); value/compare them on multiples only.
- **Yahoo snapshot has known bad points** (e.g. `dividend_yield` corrupt; margins/ROE stored in percent-form while multiples are plain numbers). Treat as-stored; don't over-trust a single value. (Root-cause fix tracked separately in `scrape_yahoo.py`.)
- **IBKR ticker quirks:** IBKR uses a space for share classes — `BRK-B → "BRK B"` via `IBKR_SYMBOL_MAP` in `scrape_ibkr.py` (stored ticker stays `BRK-B`).
- **`PORTFOLIO`** is a pseudo-instrument (`asset_class='account'`) holding IBKR account-summary metrics (netliquidation, cash…) — not a security; the price scraper skips it.
- **Secrets** (SEC_IDENTITY, SMTP creds, API keys) live in `.env` (gitignored). Never commit them.

## Automation & alerting
`run_daily.sh` (launchd) runs `update.py` then `health_check.py`, logging to `scraper.log`. Health check emails on **stale data** or a **non-IBKR source down** — but **IBKR connectivity failures never alert** (IB Gateway is flaky and self-recovers; Yahoo fallback keeps prices fresh meanwhile).

## Learning layer
The repo doubles as a study loop: `LEARNING_LOG.md` tracks progress (order mechanics, risk sizing, and the valuation module); `PHILOSOPHY.md` holds the investing principles to **consult before any financial suggestion** (margin of safety, survivability, evidence-based). Two journals: `investment/` (hold) and `trade/` (active).

## Current footprint (~2026-07, approximate — will drift)
~183 instruments (142 stocks + ETFs/bonds/…), ~220k prices, ~10k metrics (120 companies with EDGAR history), ~4.3k filings, ~46k news, 23 industries.
