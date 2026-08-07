# Strategy Research Log — 🔬 Quant Book

Every strategy I research: hypothesis, exact rules, backtest method, results, verdict,
lessons — so I never re-learn the same lesson. Complements the Trade Journal (bracketed
trades), Investment Journal (long-term holds), and PHILOSOPHY.md.

**Rule:** a strategy graduates to real money only via **backtest → paper → live**. Never skip a stage.

---

## Methodology principles (apply to EVERY strategy)

1. **One backtest lies.** Test the *distribution* over many rolling windows, not one path.
   *(A single 2021–26 window made fixed dips look BEST; across 259 windows, WORST.)*
2. **Buy-and-hold is brutally hard to beat.** Markets trend up; holding cash to wait for dips is a drag.
3. **Judge risk-adjusted (Sharpe) + max drawdown, not raw return.**
4. **Win rate is a trap — judge expectancy** (win%×avg-win + loss%×avg-loss).
   *(Fixed-dip beat B&H 48% of windows yet had −17% expectancy.)*
5. **Test assumption sensitivity** — one assumption can flip the conclusion.
   *(Cash yield 0%→4% flipped S1's Sharpe verdict.)*
6. **Round, simple, relative (%) rules beat fixed/optimized ones** on a rising asset — fixed
   price levels go stale as the index climbs.
7. **For a contribution stream, measure money-weighted IRR** (not final÷contributed).
   *(S2: DCA IRR 18.0% > QQQ CAGR 15.3%, because the boom was back-loaded.)*
8. **Regular contributions are already automatic dip-buying** — you buy every crash — so an
   explicit dip overlay adds almost nothing on top. *(S2.)*

---

## Strategies

### S1 — Dip-buying a lump sum on index ETFs vs buy-and-hold
- **Status:** Backtested only. Not deployed. · **Date:** 2026-08-02 · **Type:** systematic entry.

**Rules:** $30k budget, 3×$10k tranches, each fires once, hold to end; idle cash @4%.
Two versions — **Fixed** (−5/−10/−15% below START price) and **Relative** (below running PEAK).
Benchmark: buy-and-hold (all $30k day 1). Universe SPY, QQQ.

**Method:** one 2021–26 window (the trap) + **259 rolling 5-yr windows** (~25y, monthly starts,
adjusted close = total return).

**Rigorous results (259 windows, 4% cash):**
| SPY | Med ret | Sharpe | Med maxDD | Worst 5yr | Beat B&H |
|---|---|---|---|---|---|
| Buy & hold | **71.8%** | 0.76 | −33.7% | −28.9% | — |
| Fixed | 30.1% | 0.39 | −15.1% | **−3.0%** | 48% |
| Relative | 58.7% | **0.82** | −26.1% | −27.3% | 48% |

| QQQ | Med ret | Sharpe | Med maxDD | Worst 5yr | Beat B&H |
|---|---|---|---|---|---|
| Buy & hold | **106.6%** | 0.79 | −35.1% | −65.8% | — |
| Fixed | 50.4% | 0.51 | −16.5% | −60.6% | 43% |
| Relative | 99.4% | **0.81** | −31.2% | −62.7% | 48% |

**Expectancy (the sharpest finding — win rate lies):**
| | Win rate vs B&H | Avg WIN | Avg LOSS | Expectancy |
|---|---|---|---|---|
| SPY fixed | 48% | +23% | −54% | **−17%** |
| SPY relative | 48% | +10% | −20% | **−5%** |
| QQQ fixed | 43% | +23% | −88% | **−41%** |
| QQQ relative | 48% | +12% | −26% | **−8%** |

**Findings:**
- **Buy-and-hold wins raw return** and ~52% of windows.
- **Relative dips:** higher Sharpe (0.82 vs 0.76) + lower drawdown = a *smoother ride, not more return*.
- **Fixed dips:** capital-preservation profile (worst 5-yr −3% SPY) but low return, weak Sharpe.
- **Win rate ≠ quality:** fixed "beat" B&H 48% of windows yet −17% expectancy (small wins, big
  losses). Expectancy separated fixed (−17%) from relative (−5%); win rate couldn't.
- The lucky single window (+115%) **reversed** under rigorous testing — the overfitting lesson, lived.

**Caveats:** overlapping windows (~5 independent 5-yr periods → the Sharpe edge is likely noise);
one market/era (US 2000–26 was exceptional; assumes the index recovers); idealized (rf=0, no
tax/slippage, constant 4% cash); assumes emotionless execution into crashes. **S1 is an ENTRY
technique, not an edge** — after the tranches deploy it's just buy-and-hold.

**Code:** [`backtests/dip_backtest.py`](backtests/dip_backtest.py) (single),
[`backtests/dip_rigorous.py`](backtests/dip_rigorous.py) (rolling).

---

### S2 — Deploying a monthly income stream (QQQ 2005→26)
- **Status:** Backtested only. Not deployed. · **Date:** 2026-08-04 · **Type:** accumulation of a recurring stream.

**Setup:** $50k arrives every month (260 months, $13.0M total in). Base DCA buys **X%** of each
paycheck immediately; the rest is a **reserve** deployed on dips (−10%/−20% below the running peak,
each fires once/episode, resets on a new high); idle cash @4%. Benchmark: **pure DCA** (100% each
month). Judged on **IRR + max drawdown** (money-weighted, single 2005-start path).

**Core — cash-cap sweep (base 50%):**
| Strategy | IRR | Max DD | Avg idle |
|---|---|---|---|
| Pure DCA (100%) | **18.0%** | −43.1% | $0 |
| cap 1 mo | 18.0% | −42.1% | $45k |
| cap 2 mo | 17.9% | −41.1% | $94k |
| cap 3 mo | 17.9% | −40.1% | $143k |
| cap 6 mo | 17.8% | −37.2% | $287k |

→ More reserve = smaller drawdown, slightly less return. A **smoother ride, not more money.**
The cap "raise the DCA when cash piles up" rule keeps effective deployment near 100%.

**Finding A — the base-buy fraction is the REAL knob (no cap):**
| Base % | Avg reserve | Dip $ used | IRR | Max DD | Final |
|---|---|---|---|---|---|
| 30% | $5.48M | $1.25M | 12.5% | −23.5% | $60M |
| 50% | $3.72M | $1.25M | 14.8% | −28.8% | $81M |
| 70% | $1.96M | $1.25M | 16.5% | −32.8% | $103M |
| 100% (=DCA) | $0 | — | 18.0% | −43.1% | $127M |

→ Base 100%→30% costs **5.5 pts of IRR** for ~20 pts of drawdown reduction — a *steep* trade.
The cap sweep looked "free" only because the cap **force-deploys** the reserve (~100% invested);
once cash is genuinely withheld (low base %, no cap), the cost is severe.

**Finding B — dips are too rare to matter.** The −10/−20% ladder triggers just **25 times over
21 years (20× −10%, 5× −20%)** and absorbs only **~$1.2M total**, regardless of reserve size. Any
reserve beyond ~$1.2M is pure cash drag. This is the root cause behind every S2 result.

**Finding C — dynamic ratio = a thermostat ≈ the tightest cap.** Raising the buy ratio as the
reserve grows (50%→75%→100%→150%→200% at 1/2/3/4 mo of reserve) reacts to *cash piling up*, never
to price — no forecasting. It self-settles at ~1 mo reserve → **IRR 18.0%, DD −42.1% (CAGR 15.5%)**,
≈ cap-1mo, and **rescues fixed-50% from its cash drag** (14.8% → 18.0% IRR). Fixed 50% *without*
the adjustment leaves CAGR 12.6% / IRR 14.8% — the adjustment is what recovers the lost return.

**Finding D — dip-grid shape (base 50%, no cap):**
| Dip grid | Buys / $ | CAGR | IRR | Max DD |
|---|---|---|---|---|
| Coarse −10/−20 | 25 / $1.25M | 12.6% | 14.8% | −28.8% |
| Fine, equal (−10→−30, step 2%, $30k ea) | 74 / $2.22M | 13.3% | **15.5%** | −30.2% |
| Fine, escalating ($10k→$50k, deeper=bigger) | 74 / $1.62M | 12.9% | 15.1% | −29.4% |

→ A finer grid helps only because it **deploys more** (closer to DCA), not because laddering is
smart. **"Buy more the deeper it falls" is WORSE** — it backloads big tranches onto deep dips that
almost never come, under-deploying at the frequent shallow ones. Correct instinct is the opposite.

**Verdict:** in a mostly-rising market, **deploying beats waiting**. Every reserve/dip/grid variant
trades return for a smoother ride; none beats pure DCA on return. The dip machinery's real (small)
value is drawdown reduction — and even that comes mostly from *holding less exposure*, not clever
timing. Best compromise found: **dynamic ratio + a fine equal grid** (deploys the reserve so it
doesn't rot, while smoothing entry).

**Caveats:** single path (2005 start), not rolling windows; one asset/era (QQQ 21.5× — 18% is NOT a
forward expectation); constant 4% idle cash (really 0–5%); no tax/slippage; contribution-cushioned
drawdown reads milder than a lump sum's (−43% here vs QQQ lump −53% in 2008); assumes you keep
contributing and buy into crashes.

**Next steps (open):**
- **Rolling-window S2** (like `dip_rigorous.py`) — turn the single path into a distribution.
- **Sharpe for S2** (not yet computed); **cash-yield sensitivity** (0/2/4/5%).
- **Take-profit (止盈) overlay** — trim a slice to cash on big run-ups, buy back per rule; target
  **max drawdown ≤ 20%** (current best −37%). Never sell the top — only trim at highs.
- Grid cap defined as **% of remaining cash** (deploying 100% of reserve maximizes drawdown).

**Code:** [`backtests/dca_dip_backtest.py`](backtests/dca_dip_backtest.py) — `dca` / `s2` (cap) /
`dyn` modes + base-fraction sweep. Standalone (yfinance), run from repo root with the venv active.

---

### S3 — Trend following (CTA) on a cross-asset ETF basket
- **Status:** Backtested (Phase-2 basic, historical only). **Not deployed.**
- **Date:** 2026-08-07
- **Type:** Systematic trend / time-series momentum. (See [`../TREND_FOLLOWING_PLAN.md`](../TREND_FOLLOWING_PLAN.md).)

**Hypothesis:** holding a diversified basket only while each asset trends up (price >
200-day MA), inverse-vol sized, beats buy-and-hold on risk-adjusted return + drawdown.

**Rules:**
- Universe: **8 ETFs across asset classes** — SPY, QQQ, EFA, EEM, TLT, GLD, DBC, UUP.
- Signal: hold an asset while **price > 200-day SMA**; else that sleeve → **cash @4%**.
- Sizing: **inverse-volatility** (risk parity) across in-trend assets; normalize by TOTAL
  inv-vol so out-of-trend sleeves sit in cash. Monthly rebalance. 2007–2026.

**Results:**
| Strategy | CAGR | Vol | Sharpe | Max DD |
|---|---|---|---|---|
| **Trend (S3)** | 7.0% | **6.2%** | **0.50** | **−7.0%** |
| Buy & hold SPY | **11.2%** | 19.8% | 0.44 | −53.4% |
| Buy & hold basket (EW) | 7.4% | 11.9% | 0.33 | −33.9% |

**Crisis check:** 2008 Trend **+6.6%** vs SPY −36.8% · 2022 **+2.1%** vs −18.2% ·
2018 +2.3% vs −4.6% · 2020 +10.1% vs +18.3% (lagged the V-recovery).

**Findings:**
- **Classic trend profile:** gives up raw return (7% vs SPY 11%) but **crushes drawdown
  (−7% vs −53%)** and edges Sharpe (0.50 vs 0.44).
- **Crisis alpha is real** — made money in 2008 and 2022 while SPY fell hard.
- **The 15% goal — leverage was the hypothesis; Phase 3 tested it and it FAILED.** Vol is
  only 6.2% → looked hugely under-levered. *Naive projection was: lever ~2.4× → ~15%.* **Phase
  3 (below) disproved that** — with honest financing + costs, leverage reached only ~8.5% at
  2.9× while Sharpe FELL and drawdown blew to −23%. Lesson: **15% needs a higher-Sharpe base
  (more markets/diversification), NOT leverage.**
- **Weakness:** whipsaw in sharp V-recoveries (2020 lagged); single 200-day signal is crude.

**Phase-3 update (2026-08-07) — vol-targeting + multi-speed (50/100/200) + costs/financing:**
| Version | CAGR | Vol | Sharpe | Max DD | Avg lev |
|---|---|---|---|---|---|
| Base (no target) | 6.8% | 5.7% | **0.49** | **−6.9%** | 1.0× |
| Vol-target 10% | 7.6% | 11.2% | 0.36 | −16.2% | 2.0× |
| Vol-target 15% | 8.2% | 14.7% | 0.34 | −22.5% | 2.6× |
| Vol-target 20% | 8.5% | 16.1% | 0.35 | −23.1% | 2.9× |

**Honest correction:** leverage barely moved return (6.8%→8.5%) but tripled vol, blew
drawdown −7%→−23%, and **cut Sharpe 0.49→0.35.** Why: 5% financing + transaction costs +
vol-targeting gets *max-levered right before vol spikes* (classic pitfall). **Leverage can't
create Sharpe, only scale it (minus costs).** → **15% is NOT reachable by levering this
8-ETF basket.** Get there via a **higher-Sharpe base** (real futures across dozens of
markets — 8 ETFs under-diversify — better signals, or combining strategies). The **unlevered
base (Sharpe 0.49, −7% DD) is the sweet spot** — an excellent diversifier, not a 15% engine.
Code: [`backtests/trend_voltarget.py`](backtests/trend_voltarget.py).

**Verdict:** a legitimate low-drawdown, positive-Sharpe **base**. 15%/yr is reachable via
vol-targeting + modest leverage — eyes open on the higher drawdown that brings. Not deployed.

**Next steps:** Phase 3 (multi-speed fast+slow signals, **vol-targeting**, transaction
costs); Phase 4 (rolling windows, out-of-sample, the leverage↔drawdown trade-off); then
paper-trade (Phase 5).

**Code:** [`backtests/trend_backtest.py`](backtests/trend_backtest.py). Standalone (yfinance).

---

*Template for the next entry — copy this:*
```
### S# — <name>
- Status: · Date: · Type:
**Rules:**
**Method:**
**Results:**
**Findings:**
**Verdict:**
**Caveats:**
**Next steps:**
**Code:**
```
