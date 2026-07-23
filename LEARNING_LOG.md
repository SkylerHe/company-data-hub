# Learning Log — IBKR Trading + CFA L1

Track what you've actually learned, with dates so progress is traceable.
**Legend:** ✅ learned & applied · 🔄 in progress · ⬜ not started

> ⭐ **Latest (2026-07-22):** Started the **Valuation** module (CFA Equity). Walked the full **DCF** — discounting/time value, free cash flow, 2-stage forecast, terminal value (Gordon growth), **CAPM** & **WACC** — plus **DCF vs comps vs LBO**, and began **multiples** (EV definition, earnings ladder, ROE, **P/E & EPS**, normalized earnings). Used `valuation.py`/`value-company` on MSFT: intrinsic ≈ $157 vs price ~$398; reverse-DCF implies the market is pricing ~30% FCF growth.
>
> *(Prev 2026-07-16: completed the full trading loop — trailing stops, scaling-out, journaling, expectancy, finding setups.)*

---

## Order mechanics
| Concept | Status | Date | Where it maps |
|---|---|---|---|
| Bid / ask / spread | ✅ | 2026-07-15 | Training B.1 · CFA Equity 6.1 |
| Market order | ✅ | 2026-07-15 | Training C.1 · CFA Equity 6.1 |
| Limit order | ✅ | 2026-07-15 | Training C.2 · CFA Equity 6.1 |
| Stop (stop-market) order | ✅ | 2026-07-15 | Training C.3 · CFA Equity 6.1 |
| Stop-limit order | 🔄 | — | Training C.4 |
| Time in force (DAY vs GTC) | ✅ | 2026-07-15 | Training D.1 · CFA Equity 6.1 |
| Bracket order | ✅ | 2026-07-15 | Training C.6 |
| OCA / One-Cancels-Another | ✅ | 2026-07-16 | Training C.6 / 4.2 · CFA Equity 6.1 |
| Buy-side OCA (short exits / entry choice) | ✅ | 2026-07-16 | Training C.6 |
| **Trailing stop** | ✅ | **2026-07-16** | Training C.5 |

## Risk & sizing
| Concept | Status | Date | Where it maps |
|---|---|---|---|
| Risk-first thinking (why loss is step 1) | ✅ | 2026-07-15 | Training F.1 |
| Risk-per-trade (1% = $10k on $1M) | ✅ | 2026-07-15 | Training F.1 |
| Position sizing (shares = risk ÷ stop distance) | ✅ | 2026-07-15 | Training F.1 · CFA Quant/PM |
| R-multiples & risk:reward | ✅ | 2026-07-15 | Training F.2 |
| Position & total-risk caps (20% / 5R) | ✅ | 2026-07-15 | Training F.3 |
| Correlation risk (same-day entries move together) | ✅ | 2026-07-16 | Training F.3 · CFA PM (Topic 10) |
| Expectancy | ✅ | 2026-07-16 | Training F.2 · CFA Quant (Topic 2) |

## Trade management (Lesson 2 ✅)
| Concept | Status | Date | Where it maps |
|---|---|---|---|
| Two books: invest (hold) vs trade | ✅ | 2026-07-15 | Training A · CFA PM |
| Support/resistance from real data (pivots) | ✅ | 2026-07-15 | evidence-based, `finance.db` |
| Move stop to breakeven (+ breakeven-plus) | ✅ | 2026-07-16 | Training G.2 |
| Trailing under confirmed higher lows | ✅ | 2026-07-16 | Training G.2 |
| Scaling out (concept; skip on tiny size) | ✅ | 2026-07-16 | Training G.2 |
| Daily P&L vs Unrealized P&L | ✅ | 2026-07-16 | portfolio reading |

## Journaling & review (Lessons 4–5 ✅)
| Concept | Status | Date | Where it maps |
|---|---|---|---|
| Trade journal (`trade/TRADE_JOURNAL.md`) | ✅ | 2026-07-16 | Training J.1 |
| Win rate / avg win-loss (R) | ✅ | 2026-07-16 | CFA Quant (Topic 2) |
| Expectancy & profit factor | ✅ | 2026-07-16 | CFA Quant (Topic 2) |
| Sample-size caveat (~20–30 trades) | ✅ | 2026-07-16 | CFA Quant |

## Finding trades / edge (Lesson 6 ✅)
| Concept | Status | Date | Where it maps |
|---|---|---|---|
| What an "edge" is (why random loses) | ✅ | 2026-07-16 | CFA Equity 6.3 (efficiency) |
| Setups: pullback / breakout / support bounce | ✅ | 2026-07-16 | Training 9 |
| Entry trigger & confirmation (don't catch a falling knife) | ✅ | 2026-07-16 | Training 9 |
| Test an edge on paper before trusting it | ✅ | 2026-07-16 | Training 9 + J |

## Valuation & multiples — CFA Equity (module started 2026-07-22)
Tool: `valuation.py` + `value-company` skill. Practiced live on MSFT.

**DCF & cost of capital**
| Concept | Status | Date | Where it maps |
|---|---|---|---|
| Time value of money / discounting (future $ < today $) | ✅ | 2026-07-22 | CFA Quant TVM · Equity DCF |
| Free cash flow (cash a business "throws off") | ✅ | 2026-07-22 | CFA Equity — FCF |
| 2-stage DCF (5-yr forecast → present value) | ✅ | 2026-07-22 | CFA Equity — DCF/DDM |
| Terminal value + Gordon growth (perpetuity intuition, why needed) | ✅ | 2026-07-22 | CFA Equity — Gordon growth |
| Perpetuity math (why ÷ r, not ÷ (1+r)) | ✅ | 2026-07-22 | CFA Quant |
| CAPM cost of equity (rf + β·ERP; beta & ERP explained) | ✅ | 2026-07-22 | CFA PM — CAPM |
| WACC + after-tax cost of debt (tax shield) | ✅ | 2026-07-22 | CFA Corp Finance — WACC |
| Reverse DCF (what growth the price implies) | ✅ | 2026-07-22 | applied via valuation.py |

**Valuation approaches**
| Concept | Status | Date | Where it maps |
|---|---|---|---|
| DCF vs comps vs LBO (absolute vs relative; what "comps" are) | ✅ | 2026-07-22 | CFA Equity — approaches |
| Method of comparables vs forecasted fundamentals | 🔄 | 2026-07-22 | CFA Equity — multiples |

**Multiples**
| Concept | Status | Date | Where it maps |
|---|---|---|---|
| Two families: equity (price) vs enterprise-value multiples | ✅ | 2026-07-22 | CFA Equity — multiples |
| Enterprise Value (full formula: +pref +debt +minority −cash) | ✅ | 2026-07-22 | CFA Equity — EV |
| Earnings ladder (Revenue→EBITDA→EBIT→Net income) | ✅ | 2026-07-22 | CFA FRA / Equity |
| ROE + DuPont (margin × turnover × leverage) | 🔄 | 2026-07-22 | CFA FRA — DuPont |
| Market cap vs book equity; P/B ↔ ROE link | 🔄 | 2026-07-22 | CFA Equity — P/B |
| **P/E** — trailing vs forward, earnings yield | ✅ | 2026-07-22 | CFA Equity — P/E |
| **EPS** — basic vs diluted, wtd-avg shares, minus preferred | ✅ | 2026-07-22 | CFA FRA — EPS |
| **Normalized earnings** (cyclical trap; hist-avg & avg-ROE; CAPE) | ✅ | 2026-07-22 | CFA Equity — normalized EPS |
| ⬜ **P/B & book value** (full deep-dive) | ⬜ | — | CFA Equity — P/B |
| ⬜ **P/S** | ⬜ | — | CFA Equity — P/S |
| ⬜ **P/CF** | ⬜ | — | CFA Equity — P/CF |
| ⬜ **Dividend yield** | ⬜ | — | CFA Equity — div yield |
| ⬜ **PEG ratio** | ⬜ | — | practical / trading |
| ⬜ **EV/EBITDA & EV/Sales** (deep-dive) | ⬜ | — | CFA Equity — EV multiples |
| ⬜ **Justified leading P/E = (1−b)/(r−g)** | ⬜ | — | CFA Equity — justified multiples |

## Process & psychology
| Concept | Status | Date | Where it maps |
|---|---|---|---|
| Never widen a stop (+ the one-time correction nuance) | ✅ | 2026-07-15 | Training C.6 / G |
| Disposition effect (why brackets help) | ✅ | 2026-07-16 | CFA Equity 6.3 |
| Daily loss limit / tilt | ⬜ | — | Training J.2 |
| PDT rule | ⬜ | — | Training H.1 |

---

## Session history
- **2026-07-15** — Lesson 1: risk-first sizing, position-sizing formula, brackets. Placed & sized trades; set up study files.
- **2026-07-16** — Learned **OCA** and paired both live trades. Then **Lessons 2–6**: breakeven & trailing stops (trailed NVDA to $201, MSFT to $386), Daily vs Unrealized P&L, scaling-out concept, **trade journal** created, **expectancy/review**, and **finding setups (edge)**. Pulled fresh prices from IB Gateway. Reinforced the evidence-based-stops rule.
- **2026-07-22** — New **Valuation** module (CFA Equity), taught with `valuation.py`/`value-company` on MSFT. Covered **DCF end-to-end** (time value of money, free cash flow, 2-stage forecast, terminal value/Gordon-growth perpetuity, CAPM cost of equity, WACC + tax shield, reverse DCF), **valuation approaches** (DCF vs comps vs LBO; what "comps" are; absolute vs relative), and **multiples** (equity vs EV families, full EV formula, earnings ladder, ROE/DuPont, market cap vs book value / P/B↔ROE). Started the ratios in depth: **P/E, EPS (basic vs diluted), and normalized earnings**. Key takeaway: MSFT's conservative DCF (~$157) sits far below price (~$398) → the reverse-DCF shows the market pricing ~30% growth; a lowball model looking "expensive" ≠ genuine overvaluation.

*Next (valuation): finish the **rest of the ratios** — **P/B & book value**, **P/S**, **P/CF**, **dividend yield**, **PEG**, **EV/EBITDA & EV/Sales** deep-dive, and the **justified leading P/E = (1−b)/(r−g)**. (Still open on trading: Lesson 7 — daily loss limit, PDT rule, avoiding tilt.)*
