# Algorithmic Trading / ML4T — Study & Build Plan 🤖

A **targeted** path through Stefan Jansen, *Machine Learning for Algorithmic Trading*
(2nd ed., 858 pp., in the `papers` table) that cashes out as a real new strategy entry:
**S4 — statistical arbitrage via cointegration**. Companion to
[`TREND_FOLLOWING_PLAN.md`](TREND_FOLLOWING_PLAN.md) (S3) and
[`STRATEGY_RESEARCH.md`](STRATEGY_RESEARCH.md) (where results get logged).

## ⚠️ Honest expectation (read first)

**Two warnings, both load-bearing.**

**1. The pairs-trading edge has largely decayed.** Gatev, Goetzmann & Rouwenhorst found
~11%/yr on US pairs over 1962–2002 — but post-2002 replications show the excess return
falling toward zero after realistic costs, as the trade got crowded and execution got
faster. **Do not expect S4 to be a money-maker.** Its value is that cointegration is the
cleanest possible vehicle for learning the *full* ML4T workflow end-to-end — stationarity,
signal construction, cost modeling, and backtest hygiene — on a strategy simple enough
that when it fails, you'll know *why*. A well-executed negative result is the expected
outcome and a complete success by this repo's standards (cf. the S3 leverage finding).

**2. ML multiplies overfitting risk, it doesn't reduce it.** S1 taught that one backtest
lies with a *one-parameter* rule. A gradient-boosted model has thousands of parameters
fitting ~15 years of low signal-to-noise data. Every methodology principle in
`STRATEGY_RESEARCH.md` gets *stricter* here, not more relaxed. **Rule: no ML model enters
a strategy until the non-ML baseline it must beat is already measured.**

## Why this path (and not chapter 1 → 24)

Of the book's 23 chapters (plus an alpha-factor appendix), ~13 are ML technique and only a
handful are core trading craft. Reading front-to-back spends months before the first useful thing. The order below
is **dependency-ordered by what protects you first**:

| Order | Ch. | Why it comes here |
|---|---|---|
| 1st | **8** — The ML4T Workflow & backtest pitfalls | Survivorship/lookahead bias, data snooping, multiple-testing. This is your own methodology, formalized — read it *before* building anything new. |
| 2nd | **4** — Financial Feature Engineering / alpha factors | How to research a signal that predicts returns, and how to evaluate it *before* backtesting it. |
| 3rd | **5** — Portfolio Optimization & Performance Evaluation | Correct Sharpe/drawdown/turnover measurement, and why naive optimizers blow up out-of-sample. |
| 4th | **9** — Time-Series Models & Statistical Arbitrage | Stationarity, ADF tests, cointegration → **the S4 build**. |
| later | 6, 7, 12 | The ML core: workflow, linear models, **gradient boosting** (ch. 12 is the industry workhorse for cross-sectional factors). |
| **defer** | 16–22 | CNNs, RNNs, GANs, deep RL. Least practical for a solo trader, most seductive, highest overfit risk. Revisit only with a working non-ML baseline. |

## ⚙️ Environment note — do NOT install the book's stack

The book's code targets **Zipline / Alphalens / pyfolio**, the Quantopian stack.
Quantopian shut down in 2020; upstream Zipline is unmaintained (the living fork is
`zipline-reloaded`), and the conda environment is a known time sink. **Borrow the book's
methods, not its infrastructure.** This repo's hand-rolled pandas + yfinance backtests
([`backtests/dip_rigorous.py`](backtests/dip_rigorous.py),
[`backtests/trend_voltarget.py`](backtests/trend_voltarget.py)) are more transparent,
already work, and already encode the rolling-window discipline S4 needs.

**Data:** `finance.db` holds ~225k price rows but only from **2021-07** (~5 yrs) — enough
for a first pass, far too short to judge a statarb strategy across regimes. Pull longer
history via `yfinance` for validation, exactly as `dip_rigorous.py` does.

## The concepts to master

1. **Stationarity** — why price series are non-stationary and returns are; ADF testing.
2. **Cointegration** — two non-stationary series sharing a stochastic trend, so their
   spread *is* stationary. (Distinct from correlation; correlation is not tradeable.)
3. **The spread & hedge ratio** — building the mean-reverting series, and why the ratio
   must be estimated out-of-sample.
4. **Half-life of mean reversion** — how long the spread takes to revert; sets holding
   period and whether costs can be covered.
5. **Multiple-testing / selection bias** — screening 200 names yields ~20k pairs; some
   cointegrate by pure chance. **This is the chapter-8 trap that kills naive statarb.**
6. **Transaction costs & shorting constraints** — statarb trades often, so costs dominate;
   the short leg has borrow cost and recall risk.

## Phased plan

- **Phase 1 — Backtest hygiene** (ch. 8). Deliverable: a short written list of every bias
  in ch. 8 that S1/S2/S3 could have suffered, checked against the existing code. Cheap,
  and it audits work already done.
- **Phase 2 — Alpha factor literacy** (ch. 4 + 5). Deliverable: notes; no code required.
- **Phase 3 — S4 baseline build** (ch. 9). Cointegration screen over the `finance.db`
  universe → spread → z-score entry/exit → backtest with costs. **Must include a
  multiple-testing correction and an out-of-sample split.** Baseline to beat: buy-and-hold
  and cash-at-4%. Deliverable: `backtests/statarb_backtest.py` + S4 entry in
  `STRATEGY_RESEARCH.md`.
- **Phase 4 — Validate honestly.** Rolling windows, cost sensitivity, and the pair-selection
  bias check. Report the *distribution*, not one path. Expect this to be where S4 dies.
- **Phase 5 — Only if it survives:** ML layer (ch. 12 boosting) to *rank* candidate pairs,
  measured against the Phase-3 non-ML baseline.

## Progress

| Phase | Status | Date | Output |
|---|---|---|---|
| 1 — Backtest hygiene (ch. 8) | ⬜ | — | bias audit of S1–S3 |
| 2 — Alpha factors (ch. 4–5) | ⬜ | — | notes |
| 3 — S4 baseline (ch. 9) | ⬜ | — | `backtests/statarb_backtest.py` |
| 4 — Honest validation | ⬜ | — | S4 verdict |
| 5 — ML layer (ch. 12) | ⬜ | — | conditional on Phase 4 |
