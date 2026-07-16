# Learning Log — IBKR Trading + CFA L1

Track what you've actually learned, with dates so progress is traceable.
**Legend:** ✅ learned & applied · 🔄 in progress · ⬜ not started

> ⭐ **Latest (2026-07-16):** Completed the full trading loop — trailing stops & breakeven, scaling-out, journaling, expectancy/review, and finding setups (edge). Live: trailed NVDA stop to $201 (locked a guaranteed win), moved MSFT stop to $386.

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
| Trade journal (`TRADE_JOURNAL.md`) | ✅ | 2026-07-16 | Training J.1 |
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

*Next: Lesson 7 — the rules that keep you alive (daily loss limit, PDT rule, avoiding tilt). Then keep practicing: find a setup, size it, and journal 20+ paper trades to measure real expectancy.*
