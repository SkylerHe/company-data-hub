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
scrape_finviz  fix ▲    │                    industry.py   ───────► map-industry
scrape_edgar   stmts   │                                          company-data (refresh)
scrape_filings text    │
scrape_news    news    ┘
scrape_ibkr_account ─► account summary
  (scrape_finviz corrects the few snapshot fields Yahoo serves corrupt)
        └─ orchestrated daily by update.py + run_daily.sh, watched by health_check.py
```

## Layout (grouped by role — files are flat at repo root)
- **Collection:** `scrape_ibkr.py` (prices), `scrape_yahoo.py` (fundamentals snapshot + fallback prices), `scrape_finviz.py` (correction layer: overrides the snapshot fields Yahoo serves corrupt — book value, P/B, EV/EBITDA — plus adds ROIC/enterprise value), `scrape_edgar_financials.py` (multi-year SEC statements), `scrape_filings.py` (10-K/10-Q/8-K text), `scrape_news.py` (news), `scrape_ibkr_account.py` (portfolio/account), `scrape_ibkr_options.py` (real-time option chain: implied vol + Greeks → `option_quotes`, run locally against IB Gateway)
- **Storage:** `store.py` (schema + all DB helpers — the core), `migrate_schema.py` (one-time migration), `industries.json` (industry config), `finance.db` (gitignored, ~740 MB)
- **Analysis (read-only engines):** `analyze.py` (fundamental health), `valuation.py` (intrinsic value: DCF/CAPM/WACC/reverse-DCF/comps/scenarios), `report.py` (editable Excel model), `industry.py` (peer comparison), `volatility.py` (realized/historical vol from prices + Black-Scholes option Greeks & implied-vol solver + **IV Rank/Percentile** from `option_quotes` history, stdlib-only), `option_strategy.py` (option strategy P&L: max profit/loss/break-even + payoff table for covered call / protective put / collar / long call·put / naked short call), `analyze_position.py` (**one-shot** position analyzer: pulls the live chain → stores a snapshot → prints per-leg Greeks + net position Greeks + IV Rank + strategy P&L together; `--offline` computes from `--spot/--iv/--days` with no Gateway)
- **Skills** (`.claude/skills/`): `company-data`, `read-fundamentals`, `value-company`, `map-industry`
- **Automation:** `update.py` (smart-cadence orchestrator), `run_daily.sh` (launchd entry), `setup_automation.sh` (installs the agent), `health_check.py` (connectivity + freshness + email alerts), `dashboard.py` (local web UI), `nav_chart.py` (account NAV vs index, rebased-to-100 SVG), `.github/workflows/daily-scrape.yml`
- **Learning/journals:** `CFA_TRADING_CURRICULUM.md` (CFA↔trading study track), `LEARNING_LOG.md` (traceable progress), `CFA_PRACTICE_REVIEW.md` (running tracker of official-site practice: misses, terms, weak spots), `PHILOSOPHY.md` (investing principles), `investment/` (long-term "book"), `trade/` (active-trading "book"). CFA Level I *practice questions* are done on the official CFA website; only the review tracker lives in-repo.

## How to run
```bash
source venv/bin/activate            # all scripts assume the venv + repo-root CWD

# Analysis (read-only; name or ticker)
python analyze.py   --company MSFT              # fundamental health
python valuation.py --company MSFT              # intrinsic value + verdict
python report.py    --company MSFT              # → editable .xlsx model
python industry.py  --industry Semiconductors   # peer map (or --company NVIDIA)
python volatility.py --company QQQ               # realized/historical vol (from prices)
python volatility.py --greeks --spot 733.94 --strike 748 --days 7 --iv 19.05 --right call   # option Greeks
python volatility.py --greeks --spot 733.94 --strike 748 --days 7 --price 1.47 --right call  # solve IV from a price
python volatility.py --iv-rank QQQ                # IV Rank/Percentile (needs option_quotes history)
python option_strategy.py --strategy collar --spot 733.94 --put-strike 713 --put-premium 1.23 --call-strike 754 --call-premium 1.67   # max P&L + break-even

# Data
python update.py                    # smart refresh (prices daily, fundamentals 14d, filings 7d, news 2d)
python scrape_edgar_financials.py --company "<Name>"   # backfill statement history
python scrape_finviz.py --company "<Name>"   # correct Yahoo's corrupt snapshot fields (auto-run after fundamentals)
python health_check.py --dry-run    # status of every source (no email)
python scrape_ibkr_options.py --company QQQ --expiry 2026-08-20   # live IV+Greeks snapshot → option_quotes (needs local IB Gateway)
python analyze_position.py --strategy collar --company QQQ --expiry 2026-08-20 --put-strike 713 --call-strike 754 --basis 700   # one-shot: live Greeks + IV Rank + P&L (add --offline --spot --iv --days without Gateway)
```

## Data model (`finance.db`)
- **Instrument-centric:** `companies` is a **VIEW** over `instruments` (insert/update via triggers). Asset classes: stock, etf, fund, bond, reit, commodity, crypto, index, cash, plus **`account`** (a pseudo-class).
- **`metrics`** = `(company_id, metric, period, value, unit, source)`. Three sources, kept distinct on purpose:
  - `source='SEC/EDGAR'` → multi-year **statement trend**, `period='FY2024'…` (revenue, net_income, free_cash_flow, total_assets/equity, shares…)
  - `source='Yahoo'` → **current snapshot** of market ratios, `period` a date like `'2026-07-01'` (pe_ratio, roe, gross_margin, beta, market_cap…)
  - `source='Finviz'` → **correction layer** over the Yahoo snapshot: only the fields Yahoo serves corrupt (`book_value_per_share`, `pb_ratio`, `ev_ebitda`) plus `enterprise_value`/`roic`/`peg_ratio`. `analyze.snapshot()` **prefers Finviz over Yahoo**, so engines read the corrected value automatically; everything else stays on Yahoo. Stocks/REITs only (ETFs/ADRs skipped).
- **`prices`** = OHLCV per `(instrument_id, date)`, `source` IBKR (primary) or Yahoo (fallback). Also stores precomputed trailing SMAs `ma_20`/`ma_50`/`ma_200` (NULL until N closes exist), refreshed by `store.recompute_moving_averages()` after every price pull.
- **`option_quotes`** = timestamped option-chain snapshots per `(instrument_id, expiry, strike, opt_right)` — bid/ask/last, `underlying_price`, `implied_vol`, and Greeks (`delta`/`gamma`/`vega`/`theta`/`rho`), all as decimals. **One row per pull** (not per day): keeping every snapshot is what accrues the IV *history* that IV Rank/Percentile need. Written by `scrape_ibkr_options.py` (IB model supplies IV + delta/gamma/vega/theta; `rho` filled via `volatility.bs_greeks()`). Add/query via `store.add_option_quote()` / `store.get_option_quotes()`.
- **`industries` + `company_industries`** = **23 thematic industries** (~11 names each: Semiconductors, AI Infrastructure, Defense & Space…). **Not GICS.**
- `filings` (full text), `news` (full-text articles).
- **`papers`** = research/strategy literature (AQR, SSRN, journals): `title`, `authors`, `source`, `url`, `year`, `topic`, `strategy` (loose link to an S1/S2 entry or factor), `summary`, optional full `content`, `read_status`. Add/query via `store.add_paper()` / `store.get_papers()`. Ties each strategy back to its source research.

## Conventions & gotchas
- **Run from repo root** — `store.DB_PATH = "finance.db"` is CWD-relative.
- **Analysis engines are read-only**; collectors upsert idempotently (keyed by company+metric+period or company+url), so re-runs never duplicate.
- **EDGAR series = trend; Yahoo snapshot = current.** Keep them separate; don't mix a snapshot value into a trend.
- **Foreign/ADR names** (TSM, ASML, ARM…) have no US 10-K → no EDGAR fundamentals (show `-`); value/compare them on multiples only.
- **Yahoo snapshot has known bad points** (e.g. `dividend_yield` corrupt; `book_value_per_share`/`enterprise_value` corrupt for some names like ASML → garbage P/B & EV/EBITDA; margins/ROE stored in percent-form while multiples are plain numbers). Treat as-stored; don't over-trust a single value. The book-value/P/B/EV-EBITDA corruption is **corrected by `scrape_finviz.py`** (Finviz overrides Yahoo on those fields via `analyze.snapshot()`); the remaining Yahoo quirks are still tracked in `scrape_yahoo.py`.
- **IBKR ticker quirks:** IBKR uses a space for share classes — `BRK-B → "BRK B"` via `IBKR_SYMBOL_MAP` in `scrape_ibkr.py` (stored ticker stays `BRK-B`).
- **`PORTFOLIO`** is a pseudo-instrument (`asset_class='account'`) holding IBKR account-summary metrics (netliquidation, cash…) — not a security; the price scraper skips it.
- **Secrets** (SEC_IDENTITY, SMTP creds, API keys) live in `.env` (gitignored). Never commit them.

## Automation & alerting
`run_daily.sh` (launchd) runs `update.py`, records the day's account NAV (`scrape_ibkr_account.py --account`, one `netliquidation` point/day — needs IB Gateway, skips silently if down), then `health_check.py`, logging to `scraper.log`. Health check emails on **stale data** or a **non-IBKR source down** — but **IBKR connectivity failures never alert** (IB Gateway is flaky and self-recovers; Yahoo fallback keeps prices fresh meanwhile).

## Learning layer
The repo doubles as a study loop: `LEARNING_LOG.md` tracks progress (order mechanics, risk sizing, and the valuation module); `PHILOSOPHY.md` holds the investing principles to **consult before any financial suggestion** (margin of safety, survivability, evidence-based). Two journals: `investment/` (hold) and `trade/` (active).

## Current footprint (~2026-07, approximate — will drift)
~183 instruments (142 stocks + ETFs/bonds/…), ~220k prices, ~10k metrics (120 companies with EDGAR history), ~4.3k filings, ~46k news, 23 industries.
