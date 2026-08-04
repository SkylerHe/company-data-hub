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
7. **For a contribution stream, measure money-weighted (IRR), not (final ÷ contributed).**
   Each dollar is invested for a different length of time; IRR weights by that. It can even
   exceed the asset's buy-hold CAGR when the boom is back-loaded (more capital was at work
   in the high-return years). *(S2: DCA IRR 18.0% > QQQ CAGR 15.3%.)* And note: **regular
   contributions are already automatic dip-buying** — you buy every crash — so an explicit
   dip overlay adds little on top.

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

### S2 — DCA + dip-buying on a monthly income stream (QQQ) vs pure DCA
- **Status:** Backtested (historical only). **Not deployed.**
- **Date:** 2026-08-04
- **Type:** Accumulation / systematic deployment of a *recurring* contribution stream.

**The real question (vs S1):** S1 deployed one fixed lump sum. This is the
working-person version — **$50k arrives every month; how do you put an ongoing
income stream to work?**

**Hypothesis:** layering a dip-buying reserve + a "deploy idle cash" cap on top of
plain monthly auto-invest beats plain auto-invest.

**The rules:**
- Universe: **QQQ**, 2005→today (~21.6 yrs, 260 monthly contributions, **$13.0M total in**).
- **$50k arrives at the start of each month.**
- **Base DCA:** buy **50% of each paycheck** immediately (always in market).
- **Dip overlay:** hold the rest as reserve; deploy an extra tranche at **−10% / −20%
  below the running peak** (each fires once per drawdown, resets on a new high) — the
  S1 "relative" mechanic.
- **Cash cap:** never let idle reserve exceed **K months** of pay; deploy the excess
  (the "cash piled up → raise the DCA" rule, made mechanical). Swept **K = 1/2/3/6**.
- Idle cash earns **4%/yr**. Benchmark: **pure DCA** — 100% of each paycheck into QQQ
  the day it arrives.
- Judged on **IRR (money-weighted annual return)** + **max drawdown** — not
  (final ÷ contributed), which lies when money arrives over 21 years.

**Results (QQQ 2005–2026, 4% idle cash):**
| Strategy | Final $ | IRR/yr | Max DD | Dip buys | Avg idle $ |
|---|---|---|---|---|---|
| Pure DCA (100%) | $126.4M | **18.0%** | −43.1% | — | $0 |
| S2 cap = 1 mo | $126.1M | 18.0% | −42.1% | 25 | $45k |
| S2 cap = 2 mo | $125.4M | 17.9% | −41.1% | 25 | $94k |
| S2 cap = 3 mo | $124.8M | 17.9% | −40.1% | 25 | $143k |
| S2 cap = 6 mo | $122.9M | 17.8% | −37.2% | 25 | $287k |

*(Context: QQQ buy-hold CAGR over the window = 15.3%; the boom was **back-loaded** —
first-half 10.6%/yr, second-half 20.1%/yr.)*

**Verdict:**
- **Pure DCA wins again — by more than in S1.** Every reserve/dip/cap variant gave up
  return; none beat plain auto-invest. *You don't beat the market by holding cash.*
- **The tradeoff is real but tiny.** More reserve (higher cap) → slightly lower IRR,
  smaller drawdown. Cap = 6 mo trimmed drawdown ~6 pts (−43% → −37%) but cost 0.2 pts of
  IRR and parked ~$287k idle on average — a **smoother ride, not more money.**
- **Not a deployable edge.** If drawdown-smoothing is genuinely wanted, a small cap
  (2–3 mo) buys a few points cheaply — but the dip-timing itself adds no return.

**Key lessons:**
1. **Monthly DCA already IS automatic dip-buying.** You buy every month — *including every
   crash* — so the contribution stream already averages you in at low prices. An explicit
   dip reserve on top barely helps because the base is already catching the dips. That's
   *why* S2's effect is even smaller than S1's (a static lump sum had no ongoing buying).
2. **Money-weighted (IRR) ≠ the asset's buy-hold CAGR.** DCA IRR 18.0% > QQQ CAGR 15.3%
   — because the boom was back-loaded and DCA had more capital deployed during the
   high-return second half. IRR weights each dollar by time invested; when late years pay
   more and contributions grow, IRR > start-to-end CAGR. (Use **IRR** for "how did *my
   account* do"; **time-weighted** for "how good is the *strategy* itself.")
3. **Ongoing contributions cushion drawdown.** −43% here vs a lump-sum QQQ's ~−53% in 2008
   — new cash keeps buying through the crash. The reported DD reads milder than a
   lump-sum DD; don't compare the two head-to-head.

**Caveats:**
- **Same era/survivorship bias as S1** — 2005–26 US tech was exceptional (QQQ 21.5×).
  18%/yr is *not* a forward expectation; a flat or Japan-like era looks nothing like this.
- **Idealized** — perfect monthly execution, no taxes/slippage, constant 4% idle-cash
  yield (really swung 0–5%), one asset, **one path** (not rolling windows like S1's
  rigorous pass — a to-do).
- **Behavioral gap** — still assumes you keep buying (and deploy reserve into crashes)
  without flinching; the real failure mode is *stopping contributions* in a bear market.

**Extension (2026-08-04) — the base-buy fraction is the real knob, not the cap:**

Two follow-ups located where the actual return/risk tradeoff lives.

*(a) Graduated (dynamic) DCA ratio ≈ the tightest cap.* Replacing the hard cap with a rule
that raises the buy ratio as the reserve grows (50% at ≤1mo of reserve, 75% at 1–2mo, 100%
at 2–3mo, 150–200% above) converges to **cap-1mo**: avg reserve $46k, IRR 18.0%, DD −42.1%.
Smooth-adjust and hard-cut land in the *same place* — any rule that refuses to let cash pile
up necessarily behaves like near-pure-DCA.

*(b) Base-buy fraction sweep 30/50/70/100% (no cap) — the hidden cost, exposed:*
| Base buy % | Avg idle reserve | Dip $ ever used | IRR | Max DD | Final |
|---|---|---|---|---|---|
| 30% | $5.48M | $1.25M | 12.5% | −23.5% | $60M |
| 50% | $3.72M | $1.25M | 14.8% | −28.8% | $81M |
| 70% | $1.96M | $1.25M | 16.5% | −32.8% | $103M |
| 100% (=pure DCA) | $0 | — | 18.0% | −43.1% | $127M |

**The sharpest finding of S2:** dip-buying absorbs only **$1.25M over 21 years, no matter how
much reserve is held** — so any reserve beyond ~$1.25M is pure cash drag. Dropping the base
fraction 100%→30% costs **5.5 pts of IRR** (18.0→12.5%, −$67M final) to buy ~20 pts of
drawdown reduction — a *steep*, real return-for-smoothness trade. The earlier cap sweep only
looked "free" because the cap force-deploys the reserve (~100% invested); once cash is
genuinely withheld (low base %, no cap), the cost is severe. **Reinforced: in a mostly-rising
market, deploying beats waiting — dips are too rare to justify holding much cash.**

**Next steps:** rolling-window version (like `dip_rigorous.py`) for a distribution not one
path; cash-yield sensitivity (0/2/4/5%); regime breakdown (bull vs bear vs sideways) — the
base-fraction sweep (done) already shows "deploy it all, immediately" wins this window.

**Code:** [`backtests/dca_dip_backtest.py`](backtests/dca_dip_backtest.py). Standalone
(yfinance) — run from repo root with the venv active.

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
