# Trade Journal — 🔵 Trade Book

Active, short-term trades — each **bracketed with defined risk**. Every trade = data. Review after ~20 trades to compute stats.
*(Long-term holds live in the Investment Book → `../investment/INVESTMENT_JOURNAL.md`.)*

**Legend:** Dir = Long/Short · 1R = planned $ loss at initial stop · R = result in units of 1R

---

## Closed trades
| Date In | Date Out | Ticker | Dir | Entry | Exit | Shares | 1R $ | Result R | Result $ | Lesson |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-07-07 | 2026-07-17 | NVDA | Long | 196.46 | 200.95 (stop) | 5 | 82.30 | **+0.27R** | **+$22.45** | Trailing stop worked — exited above entry for a guaranteed win. OCA $232 target auto-cancelled on the stop fill |
| 2026-07-07 | 2026-07-20 | SPCX | Long | 126.86 | 122.72 (sold) | 100 | 886 | **−0.47R** | **−$414** | Cut the falling knife early (−$414 vs −$886 stop). Bought post-IPO hype, no margin of safety, held naked at first — the anti-example. **Bad process → bad outcome.** |
| 2026-07-07 | 2026-07-23 | MSFT | Long | 392.78 | 385.85 (stop) | 5 | 103.90 | **−0.33R** | **−$34.65** | Stop at $386 did its job — price broke the confirmed $386.40 low and filled at $385.85, cutting the loss to −0.33R vs the −1R ($103.90) initial risk. Tightening the stop to structure = controlled loss. **Good process, small loss.** |

## Active trades
| Date In | Ticker | Dir | Entry | Init Stop | Cur Stop | Target | Shares | 1R $ | Setup / Reason | Lesson |
|---|---|---|---|---|---|---|---|---|---|---|
| _None open_ | — | — | — | — | — | — | — | — | MSFT closed 2026-07-23 (see Closed trades) | — |

## Pending orders (working, not yet filled)
| Date | Ticker | Order | Note |
|---|---|---|---|
| 2026-07-17 | NVDA | BUY 10 LMT 191.59 GTC | Re-entry near the $191.14 (07-07) support. Buys the dip *at* the level — no bounce confirmation. Bracket it if it fills |

---

## Review stats
- **Total closed trades: 3** (n=3 → still pure noise; need ~20 before stats mean anything)
- Wins: 1 · Losses: 2 · Win %: 33%
- Avg win: +0.27R · Avg loss: −0.40R · **Expectancy: −0.18R/trade** · Net: −0.53R (−$426.20)
- Biggest recurring mistake so far: **buying hype with no margin of safety / no stop (SPCX)**. MSFT, by contrast, was a clean, controlled stop-out (−0.33R) — the process working as designed.

## How to log each new trade
1. On entry: fill Date In, Entry, Init Stop, Target, Shares, 1R Risk, and **Setup/Reason**.
2. On any stop move: update Cur Stop (note why in Lesson).
3. On exit: fill Date Out, Exit, Result (R and $), and **Lesson**.
