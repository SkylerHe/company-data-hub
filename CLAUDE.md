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
- **Analysis (read-only engines):** `analyze.py` (fundamental health), `valuation.py` (intrinsic value: DCF/CAPM/WACC/reverse-DCF/comps/scenarios), `report.py` (editable Excel model), `industry.py` (peer comparison), `volatility.py` (realized/historical vol from prices + Black-Scholes option Greeks & implied-vol solver + **IV Rank/Percentile** from `option_quotes` history, stdlib-only), `option_strategy.py` (option strategy P&L: max profit/loss/break-even + payoff table for covered call / protective put / collar / long call·put / naked short call), `analyze_position.py` (**one-shot** position analyzer: pulls the live chain → stores a snapshot → prints per-leg Greeks + net position Greeks + IV Rank + strategy P&L together; `--offline` computes from `--spot/--iv/--days` with no Gateway), `option_report.py` (exports a position as an **editable Excel workbook** — Position/Greeks/Payoff sheets + an embedded payoff chart — for viewing/charting on a Mac; reads a stored `option_quotes` snapshot or computes offline), `option_position.py` (shared leg-model + net-position-Greeks + `build_context()` used by the exporters), `sheets_export.py` (pushes the same Position/Greeks/Payoff data straight into a **Google Sheet** via gspread + a service account — the free, Mac-friendly path when Excel isn't licensed; `build_sheets_data()` is testable with `--dry-run`, no creds)
- **Skills** (`.claude/skills/`): `company-data`, `read-fundamentals`, `value-company`, `map-industry`
- **Automation:** `update.py` (smart-cadence orchestrator), `run_daily.sh` (launchd entry), `setup_automation.sh` (installs the agent), `health_check.py` (connectivity + freshness + email alerts), `dashboard.py` (local web UI), `nav_chart.py` (account NAV vs index, rebased-to-100 SVG), `.github/workflows/daily-scrape.yml`
- **Learning/journals:** `CFA_TRADING_CURRICULUM.md` (CFA↔trading study track), `LEARNING_LOG.md` (traceable progress), `CFA_PRACTICE_REVIEW.md` (running tracker of official-site practice: misses, terms, weak spots), `PHILOSOPHY.md` (investing principles), `investment/` (long-term "book"), `trade/` (active-trading "book"). CFA Level I *practice questions* are done on the official CFA website; only the review tracker lives in-repo.

## How to run
```bash
source venv/bin/activate            # all scripts assume the venv + repo-root CWD

# Analysis (read-only; name or ticker)
python analyze.py   --company MSFT              # fundamental health
python analyze.py   --company MSFT --common-size # multi-year common-size statements (income/balance/cash-flow)
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
python store.py --recompute-common-size      # rebuild common-size statements (%-of-revenue / %-of-assets) for all EDGAR companies
python health_check.py --dry-run    # status of every source (no email)
python scrape_ibkr_options.py --company QQQ --expiry 2026-08-20   # live IV+Greeks snapshot → option_quotes (needs local IB Gateway)
python analyze_position.py --strategy collar --company QQQ --expiry 2026-08-20 --put-strike 713 --call-strike 754 --basis 700   # one-shot: live Greeks + IV Rank + P&L (add --offline --spot --iv --days without Gateway)
python option_report.py --strategy collar --company QQQ --expiry 2026-08-20 --put-strike 713 --call-strike 754 --spot 733.94 --iv 19.05 --days 7 --basis 700   # → editable .xlsx (Position/Greeks/Payoff + chart)
```

## Data model (`finance.db`)
- **Instrument-centric:** `companies` is a **VIEW** over `instruments` (insert/update via triggers). Asset classes: stock, etf, fund, bond, reit, commodity, crypto, index, cash, plus **`account`** (a pseudo-class).
- **`metrics`** = `(company_id, metric, period, value, unit, source)`. Three sources, kept distinct on purpose:
  - `source='SEC/EDGAR'` → multi-year **statement trend**, `period='FY2024'…` (revenue, net_income, free_cash_flow, total_assets/equity, shares…)
  - `source='Yahoo'` → **current snapshot** of market ratios, `period` a date like `'2026-07-01'` (pe_ratio, roe, gross_margin, beta, market_cap…)
  - `source='Finviz'` → **correction layer** over the Yahoo snapshot: only the fields Yahoo serves corrupt (`book_value_per_share`, `pb_ratio`, `ev_ebitda`) plus `enterprise_value`/`roic`/`peg_ratio`. `analyze.snapshot()` **prefers Finviz over Yahoo**, so engines read the corrected value automatically; everything else stays on Yahoo. Stocks/REITs only (ETFs/ADRs skipped).
- **`prices`** = OHLCV per `(instrument_id, date)`, `source` IBKR (primary) or Yahoo (fallback). Also stores precomputed trailing SMAs `ma_20`/`ma_50`/`ma_200` (NULL until N closes exist), refreshed by `store.recompute_moving_averages()` after every price pull.
- **`option_quotes`** = timestamped option-chain snapshots per `(instrument_id, expiry, strike, opt_right)` — bid/ask/last, `underlying_price`, `implied_vol`, and Greeks (`delta`/`gamma`/`vega`/`theta`/`rho`), all as decimals. **One row per pull** (not per day): keeping every snapshot is what accrues the IV *history* that IV Rank/Percentile need. Written by `scrape_ibkr_options.py` (IB model supplies IV + delta/gamma/vega/theta; `rho` filled via `volatility.bs_greeks()`). Add/query via `store.add_option_quote()` / `store.get_option_quotes()`.
- **`common_size`** = **materialized common-size statements** derived from the SEC/EDGAR dollar rows in `metrics`: each line item as a decimal fraction of its base — **income** & **cash_flow** ÷ `revenue`, **balance** ÷ `total_assets`, per `(company_id, statement, line_item, period)`. Rebuilt by `store.recompute_common_size()` after every EDGAR pull (auto-run in `scrape_edgar_financials.py`, like moving averages after a price pull); a `(statement, period)` is skipped when its base is missing/zero. Query via `store.get_common_size()`; rebuild all with `python store.py --recompute-common-size`. Only the three statements get common-sized (share counts excluded; statement-of-equity has no natural base).
- **`industries` + `company_industries`** = **23 thematic industries** (~11 names each: Semiconductors, AI Infrastructure, Defense & Space…). **Not GICS.**
- `filings` (full text), `news` (full-text articles).
- **`papers`** = research/strategy literature (AQR, SSRN, journals): `title`, `authors`, `source`, `url`, `year`, `topic`, `strategy` (loose link to an S1/S2 entry or factor), `summary`, optional full `content`, `read_status`. Add/query via `store.add_paper()` / `store.get_papers()`. Ties each strategy back to its source research.

## Conventions & gotchas
- **Run from repo root** — `store.DB_PATH = "finance.db"` is CWD-relative.
- **Analysis engines are read-only**; collectors upsert idempotently (keyed by company+metric+period or company+url), so re-runs never duplicate.
- **EDGAR series = trend; Yahoo snapshot = current.** Keep them separate; don't mix a snapshot value into a trend.
- **Foreign/ADR names** (TSM, ASML, ARM…) have no US 10-K → no EDGAR fundamentals (show `-`); value/compare them on multiples only.
- **Yahoo snapshot has known bad points** (e.g. `dividend_yield` corrupt; `book_value_per_share`/`enterprise_value` corrupt for some names like ASML → garbage P/B & EV/EBITDA; margins/ROE stored in percent-form while multiples are plain numbers). Treat as-stored; don't over-trust a single value. The book-value/P/B/EV-EBITDA corruption is **corrected by `scrape_finviz.py`** (Finviz overrides Yahoo on those fields via `analyze.snapshot()`); the remaining Yahoo quirks are still tracked in `scrape_yahoo.py`.
- **Foreign filers report in two currencies.** For a non-US filer (Panasonic, TSMC, ASML, SAP, Novo Nordisk…) Yahoo quotes **price/market cap in the listing currency (USD)** but serves the **financial statements in the filer's own currency** (JPY/TWD/EUR/DKK). `scrape_yahoo.py` detects this via `info['currency'] != info['financialCurrency']` and (a) **converts** statement figures (revenue, cash, debt, assets, FCF) to USD via a cached spot rate, and (b) **skips** the ratios Yahoo builds *across* the two — `pb_ratio`, `ps_ratio`, `ev_ebitda`, `book_value_per_share` — since no scaling repairs them. Skipping also **purges** any row a pre-fix run stored (`store.delete_metric`), because `analyze.snapshot()` reads the newest row and a stale corrupt value would otherwise outlive the fix. Those four fields then come from **Finviz** where it covers the name, or show `-`.
- **IBKR ticker quirks:** IBKR uses a space for share classes — `BRK-B → "BRK B"` via `IBKR_SYMBOL_MAP` in `scrape_ibkr.py` (stored ticker stays `BRK-B`).
- **IB Gateway has two distinct failure modes, and they look identical from `ib_insync`.** (a) *Not running* → connection refused. (b) *Running and completing the API handshake, but never answering data requests* — `ib_insync.connect()` runs a mandatory startup sync (positions, orders, executions) and hangs on every phase, finally raising a `TimeoutError` **with an empty message**. That empty error is why `scrape_ibkr_account.py` logged "failed to connect" for weeks while `health_check.check_ibkr()` (a raw socket handshake, no data requests) reported OK. The scraper now probes the port first via `check_gateway()` and names which mode it hit; mode (b) needs a **Gateway restart**, not a longer timeout (measured: still timing out at 180s).
- **`PORTFOLIO`** is a pseudo-instrument (`asset_class='account'`) holding IBKR account-summary metrics (netliquidation, cash…) — not a security; the price scraper skips it.
- **Secrets** (SEC_IDENTITY, SMTP creds, API keys) live in `.env` (gitignored). Never commit them.

## Automation & alerting
**Every step in `run_daily.sh` runs under a bash wall-clock watchdog** (`run_step`, killing the whole process tree — macOS has no coreutils `timeout`). This is not optional: **launchd will not start a new instance while the previous one is still alive**, so one hung child silently cancels every future run. In Aug 2026 `scrape_ibkr.py` hung on a degraded IB Gateway and `run_daily.sh` stayed alive **7 days** — no runs, everything went stale, and *nothing alerted because `health_check.py` runs at the END of the same script it was stuck inside*. The watchdog guarantees the health check still executes.

`run_daily.sh` (launchd) runs `update.py`, records the day's account NAV (`scrape_ibkr_account.py --account`, one `netliquidation` point/day — needs IB Gateway, skips if down), then `health_check.py`, logging to `scraper.log`. Health check emails on **stale data**, a **non-IBKR source down**, or a **NAV gap over `NAV_STALE_DAYS` (7)** — but **IBKR connectivity failures never alert** (IB Gateway is flaky and self-recovers; Yahoo fallback keeps prices fresh meanwhile).

## Learning layer
The repo doubles as a study loop: `LEARNING_LOG.md` tracks progress (order mechanics, risk sizing, and the valuation module); `PHILOSOPHY.md` holds the investing principles to **consult before any financial suggestion** (margin of safety, survivability, evidence-based). Two journals: `investment/` (hold) and `trade/` (active).

## Current footprint (~2026-07, approximate — will drift)
~183 instruments (142 stocks + ETFs/bonds/…), ~220k prices, ~10k metrics (120 companies with EDGAR history), ~4.3k filings, ~46k news, 23 industries.
