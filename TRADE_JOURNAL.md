# Trade Journal

Every trade = data. Log the mechanics **and** the reasoning. Review after ~20 trades to compute stats.
Two books kept separate: **Trades** (active, bracketed) and **Investments** (buy-and-hold, no stop).

**Legend:** Dir = Long/Short · 1R = planned $ loss at initial stop · R = result in units of 1R

---

## Closed trades
| Date In | Date Out | Ticker | Dir | Entry | Exit | Shares | 1R $ | Result R | Result $ | Lesson |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-07-07 | 2026-07-17 | NVDA | Long | 196.46 | 200.95 (stop) | 5 | 82.30 | **+0.27R** | **+$22.45** | Trailing stop worked — exited above entry for a guaranteed win. OCA $232 target auto-cancelled on the stop fill |

## Active trades
| Date In | Ticker | Dir | Entry | Init Stop | Cur Stop | Target | Shares | 1R $ | Setup / Reason | Lesson |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-07-07 | MSFT | Long | 392.78 | 372 | **386** | 410 | 5 | 103.90 | _(fill in)_ | Re-anchored stop to confirmed $386.40 low |
| 2026-07-17 | SPCX | Long | 126.86 | **118** | **118** | — | 100 | 886 | Post-IPO momentum (went against me) | No support in price discovery (new lows daily) → set a hard-$ risk stop ($118 = max loss ~$886), not a support stop |

## Pending orders (working, not yet filled)
| Date | Ticker | Order | Note |
|---|---|---|---|
| 2026-07-17 | NVDA | BUY 10 LMT 191.59 GTC | Re-entry near the $191.14 (07-07) support. Buys the dip *at* the level — no bounce confirmation. Bracket it if it fills |

## Investments (buy-and-hold — no stop, not traded)
| Date In | Ticker | Entry | Shares | Notes |
|---|---|---|---|---|
| 2026-07-07 | SPY | 748.51 | 10 | Initial. Long-term S&P 500 exposure |
| 2026-07-17 | SPY | 746.88 | 90 (approx) | Added (dollar-cost averaging) → **~100 sh total, blended avg ≈ $747.04** |

---

## Review stats
- **Total closed trades: 1** (n=1 → pure noise; need ~20 before stats mean anything)
- Wins: 1 · Losses: 0 · Win %: 100% *(meaningless at n=1)*
- Avg win: +0.27R · Avg loss: — · Expectancy: +0.27R *(placeholder)*
- Biggest recurring mistake so far: _—_

## How to log each new trade
1. On entry: fill Date In, Entry, Init Stop, Target, Shares, 1R Risk, and **Setup/Reason**.
2. On any stop move: update Cur Stop (note why in Lesson).
3. On exit: fill Date Out, Exit, Result (R and $), and **Lesson**.
