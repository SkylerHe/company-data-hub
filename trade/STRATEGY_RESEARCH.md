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
3b. **Win rate is a trap — judge EXPECTANCY** = win% × avg-win + loss% × avg-loss (PHILOSOPHY
   #18). A ~50% win rate with big losses and small wins is a *losing* strategy. *(Fixed-dip
   beat B&H 48% of the time but had −17% expectancy: small wins, big losses.)*
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

**Results — win/loss margins (expectancy):** *the sharpest finding — win rate lies*
| Strategy | Win rate vs B&H | Avg WIN margin | Avg LOSS margin | Overall avg (expectancy) |
|---|---|---|---|---|
| SPY fixed | 48% | +23% | −54% | **−17%** |
| SPY relative | 48% | +10% | −20% | **−5%** |
| QQQ fixed | 43% | +23% | −88% | **−41%** |
| QQQ relative | 48% | +12% | −26% | **−8%** |

- **Win rate is misleading:** fixed "beats" B&H ~48% of the time but wins *small* (+23%) and
  loses *big* (−54%) → **expectancy −17%** — a losing strategy despite a coin-flip win rate.
- Fixed and relative have **near-identical win rates (48%)** but very different expectancy
  (−17% vs −5%) → **win rate can't tell good from bad; expectancy can.**
- Why the asymmetry: dip-buying wins *small* in bear windows (deploys lower than a top-buying
  B&H) but loses *big* in bull windows (sits in cash, misses the whole run). Markets rise more
  often → negative expectancy.

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
- **Win rate ≠ quality.** Fixed-dip "beat" B&H 48% of windows yet has −17% expectancy — small
  wins, big losses. Judge **expectancy** (size × frequency), never the beat-rate. Win rate
  couldn't even distinguish fixed (−17%) from relative (−5%); expectancy did.

**Caveats — read before trusting S1:**

*Statistical robustness (hold the numbers loosely):*
- **Overlapping windows** — 259 windows overlap heavily; ~25y holds only **~5 independent**
  5-yr periods. The relative-dips Sharpe edge (0.82 vs 0.76) is **likely within noise** — not proven.
- **One market, one era** — US SPY/QQQ, 2000–26, a period US equities were *exceptional*. May
  not hold for Japan (30y below its 1989 peak), EM, or a different future. **Dip-buying assumes
  the index always recovers — true for the US so far, not a law.**
- **Idealized mechanics** — rf=0 in Sharpe; no taxes/slippage; constant 4% cash (reality: ~0%
  in 2009–21, ~5% in 2023–24 — swings the dip strategies a lot).

*Behavioral / execution (the real gap):*
- The backtest assumes **perfect, emotionless execution.** But **buying into a −15% crash** is
  when every instinct screams sell — most people freeze or capitulate right when the rule says buy.
- **Cash drag is agonizing** — sitting in cash for years during a bull tests discipline; many
  abandon the strategy right before the dip comes. **A strategy you can't execute has expectancy 0.** (PHILOSOPHY #17, #19)

*Scope — what S1 actually is:*
- **An ENTRY technique, not an edge.** It governs *how to deploy a lump sum*, not how to beat the
  market. After the 3 tranches deploy, it's **just buy-and-hold.** Real use = **regret/drawdown
  reduction**, not alpha.

*Failure modes:*
- **Crash past level 3** (−15%+) → out of tranches, fully deployed, underwater, no plan for a −40% bear.
- **Dipless bull** (e.g. 2013–19) → dips never trigger, sit in cash, badly lag (the −54% loss case).
- **Abandonment** — quitting emotionally at the worst time.

**Next steps / to-do:**
- Compare vs **DCA** (time-based) — the more practical rival for deploying cash than lump-sum.
- Cash-yield **sensitivity sweep** (0/2/4/5%); **excess-return Sharpe**; recurring-**grid** variant.
- Regime breakdown (bull vs bear vs sideways); other assets/eras for robustness.

**Meta-takeaway:** the real value of S1 was learning the **method** (test the distribution, judge
on Sharpe + expectancy, check assumption sensitivity, distrust a winning backtest) — that transfers
to every future strategy. S1 fooled us first (the +115% window), then taught us to catch it.

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
