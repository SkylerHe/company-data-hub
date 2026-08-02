# Strategy Research Log — 🔬 Quant Book

A running log of every trading strategy I research: the **hypothesis, exact rules,
backtest method, results, verdict, and lessons** — so I can refer back and never
re-learn the same lesson. Complements the **Trade Journal** (actual bracketed trades),
the **Investment Journal** (long-term holds), and **PHILOSOPHY.md** (principles).

**Rule:** a strategy only graduates to real money via **backtest (historical) →
forward-test (paper) → live**. Never skip a stage.

---

## Quant methodology principles (reusable — apply to EVERY strategy)

Hard-won lessons that matter regardless of the strategy:

1. **One backtest lies.** Test the *distribution* across many **rolling windows**, not one
   lucky path. *(A single 2021–26 window made fixed-dollar dips look BEST; across 259
   windows it was the WORST. Same strategy, opposite conclusion.)*
2. **Buy-and-hold is the benchmark, and it's brutally hard to beat.** Markets trend up,
   so holding cash to wait for dips is a drag. Most "clever" strategies lose to it on return.
3. **Judge on risk-adjusted return (Sharpe) + max drawdown — not raw return.** Raw return
   hid that relative-dips matched/beat buy-hold once risk was accounted for.
4. **Test assumption sensitivity.** One assumption can flip the conclusion. *(Cash yield
   0% → 4% flipped relative-dips from Sharpe-tied to Sharpe-ahead.)*
5. **Beware overfitting / curve-fitting.** Round, fixed, simple rules beat rules optimized
   to past data. Don't tune levels to make history look good.
6. **Relative (%) rules > fixed-dollar rules** for a long-term, upward-trending asset —
   fixed prices go stale as the index climbs.

---

## Strategies

### S1 — Dip-buying on index ETFs (fixed vs relative) vs buy-and-hold
- **Status:** Backtested (historical only). **Not deployed.**
- **Date:** 2026-08-02
- **Type:** Mean-reversion / systematic entry.

**Hypothesis:** buying a broad index in tranches on dips beats lump-sum buy-and-hold.

**The rules:**
- Universe: **SPY, QQQ** (broad, diversified indices — historically recover; far safer to
  average down than a single stock — see PHILOSOPHY #6, the SPCX "falling knife" lesson).
- Budget **$30k**, **3 equal tranches of $10k**. Each tranche fires once; hold to end.
- Undeployed cash earns **4%/yr** (realistic T-bill/money-market rate).
- Two versions:
  - **Fixed-dollar:** buy at **−5 / −10 / −15% below the START price** (fixed forever).
  - **Relative:** buy at **−5 / −10 / −15% below the running PEAK** (adapts as it rises).
- Benchmark: **buy-and-hold** (all $30k on day 1).

**Backtest method:**
- **Lucky-path pass:** single 2021–26 window (from `finance.db`).
- **Rigorous pass:** **259 rolling 5-yr windows**, monthly starts, ~25 yrs SPY/QQQ
  (yfinance, adjusted close = total return). Metrics: total return, annualized Sharpe
  (rf=0 in ratio), max drawdown, and % of windows that beat buy-and-hold.

**Results — single window (2021–26):** *dip-buying looked great (the trap)*
| | QQQ buy-hold | QQQ fixed | QQQ relative |
|---|---|---|---|
| Return | +91% | **+115%** | +94% |
- Fixed-dollar looked BEST here — but this was one lucky path (a big 2022 drawdown early, then recovery).

**Results — rigorous (259 windows, 4% cash):** *the honest picture*
| SPY | Median ret | Sharpe | Med maxDD | Worst 5yr | Beat B&H |
|---|---|---|---|---|---|
| Buy & hold | **71.8%** | 0.76 | −33.7% | −28.9% | — |
| Fixed-dollar | 30.1% | 0.39 | −15.1% | **−3.0%** | 48% |
| Relative | 58.7% | **0.82** | −26.1% | −27.3% | 48% |

| QQQ | Median ret | Sharpe | Med maxDD | Worst 5yr | Beat B&H |
|---|---|---|---|---|---|
| Buy & hold | **106.6%** | 0.79 | −35.1% | −65.8% | — |
| Fixed-dollar | 50.4% | 0.51 | −16.5% | −60.6% | 43% |
| Relative | 99.4% | **0.81** | −31.2% | −62.7% | 48% |

**Verdict:**
- **Buy-and-hold wins raw return** and ~52% of windows. *You don't beat the market by
  holding cash.*
- **Relative dips:** slightly higher Sharpe (0.82 vs 0.76) + lower drawdown → a legitimate
  **"smoother ride,"** NOT a return booster. Give up return for less risk.
- **Fixed-dollar dips:** **capital-preservation** profile (worst 5-yr just −3% on SPY,
  mostly sits in cash at 4%) but low return and weak Sharpe. Only if the sole goal is
  "never lose much."
- **Not a deployable edge for growth.** If ever used, use *relative* levels, for drawdown
  reduction, eyes open to the return give-up.

**Key lessons (see also the methodology principles above):**
- The single window **reversed** under rigorous testing → the overfitting lesson, lived.
- The 4% cash assumption **flipped** the Sharpe result → assumption sensitivity is real.
- Dip-buying = **risk/return trade** (lower drawdown, lower return), not a free lunch.

**Caveats / next steps:**
- Overlapping windows (effective sample < 259); Sharpe uses rf=0 (excess-return Sharpe would
  refine it); one-shot deployment (not a recurring grid); no transaction costs.
- To do: cash-yield sensitivity sweep (0/2/4/5%); recurring-grid variant; excess-return Sharpe.

**Code:** [`backtests/dip_backtest.py`](backtests/dip_backtest.py) (single window),
[`backtests/dip_rigorous.py`](backtests/dip_rigorous.py) (rolling windows). Reproducible —
run from repo root with the venv active.

---

*Template for the next entry — copy this:*
```
### S# — <name>
- Status: · Date: · Type:
**Hypothesis:**
**Rules:**
**Backtest method:**
**Results:**
**Verdict:**
**Key lessons:**
**Caveats / next:**
**Code:**
```
