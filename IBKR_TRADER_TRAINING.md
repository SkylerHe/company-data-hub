# IBKR Active Trader Training — iPad Simulated Platform

A hands-on guide to becoming fluent and disciplined placing trades on the **IBKR iPad paper account**.
Every concept follows the same shape:

> **What it is (plain)** → **The logic / why** → **On the iPad** → **Example** → **Drill** → **Common mistake**

### 🎓 CFA overlap badge
Concepts marked **🎓 Also in CFA L1** are *also tested on the CFA Level 1 exam* — study them once, count them twice.
The badge points to the exact lesson (see `CFA_TRADING_CURRICULUM.md`). These are your highest-leverage topics.

---

## Part A — Platform Orientation (iPad)

### A.1 The layout
- **What it is:** Watchlist → tap a symbol → Quote/Chart page → **Buy/Sell** buttons open the order ticket.
- **The logic / why:** Fast, repeatable navigation is the base skill — hesitation costs money when exiting.
- **On the iPad:** Build a watchlist of 3–5 liquid names (e.g. SPY, MSFT, NVDA). Learn where the ticket, positions, and orders tabs live.
- **Drill:** Time yourself opening a ticket and cancelling it — get under 10 seconds.
- **Common mistake:** Trading names you can't see at a glance; keep your watchlist tight.

### A.2 Paper vs. live differences
- **What it is:** The sim fills you optimistically and carries no real emotion.
- **The logic / why:** Paper proves *mechanics and discipline*, not that you're profitable — real fills have slippage and fear.
- **Common mistake:** Believing paper P&L predicts live P&L. It doesn't. Judge yourself on process.

---

## Part B — Reading Price

### B.1 Bid / Ask / Spread   🎓
> **🎓 Also in CFA L1 — Equity 6.1 *Market Organization & Structure*** (market microstructure)
- **What it is:** Bid = best price a buyer will pay; Ask = best a seller will take; Spread = the gap.
- **The logic / why:** You buy at the ask, sell at the bid — the spread is a cost you pay instantly on entry.
- **On the iPad:** The quote page shows bid/ask and sizes; watch them move in real time.
- **Example:** NVDA $130.00 bid / $130.05 ask → buy at $130.05, and you're immediately "down" the $0.05 spread.
- **Drill:** Compare spreads on SPY (tight) vs. a small stock (wide). Notice liquidity's effect.
- **Common mistake:** Trading wide-spread names actively — the spread eats your edge.

### B.2 Liquidity, volume, slippage   🎓
> **🎓 Also in CFA L1 — Equity 6.1** (order execution / market quality)
- **What it is:** Liquidity = how easily you trade without moving price; slippage = getting a worse fill than expected.
- **The logic / why:** Thin markets punish market orders; size and urgency both cost you.
- **Drill:** Send a small market order on SPY, then note fill vs. the ask you saw. Repeat on a thinner name.

---

## Part C — Order Types (the core vocabulary)

### C.1 Market order   🎓
> **🎓 Also in CFA L1 — Equity 6.1** (execution instructions)
- **What it is:** "Fill me now at whatever price is available."
- **The logic / why:** Buys *certainty of execution*, pays with spread + slippage. Use only when getting done matters more than the price.
- **On the iPad:** Order Type = **MKT** → Preview → submit.
- **Example:** Your 5-share MSFT buy filled instantly at the ask.
- **Common mistake:** Using market orders on illiquid names or in fast markets.

### C.2 Limit order   🎓
> **🎓 Also in CFA L1 — Equity 6.1** (limit orders)
- **What it is:** Fills at your price *or better*, never worse.
- **The logic / why:** Trades certainty of execution for control of price. Your default for active entries.
- **On the iPad:** Order Type = **LMT** → set price → set TIF → Preview.
- **Example:** Buy limit NVDA $129.50 — fills only at $129.50 or lower; if price runs up you simply don't fill.
- **Drill:** Place one below price (watch it sit "working"), then one at the ask ("marketable limit," fills instantly).
- **Common mistake:** Forgetting the TIF and leaving a stale limit alive.

### C.3 Stop (stop-market)   🎓
> **🎓 Also in CFA L1 — Equity 6.1** (stop orders)
- **What it is:** A trigger — once price hits your stop, it becomes a *market* order.
- **The logic / why:** Defines and caps your loss automatically, but inherits market-order slippage when triggered.
- **On the iPad:** Order Type = **STP** → set stop price.
- **Example:** Long NVDA at $130, sell stop $125 — if it falls to $125 it auto-sells to stop the loss.
- **Common mistake:** Placing stops at obvious round numbers where everyone else's sit.

### C.4 Stop-limit
- **What it is:** A stop that becomes a *limit* (not market) when triggered.
- **The logic / why:** Caps your exit price — but may fail to fill in a fast drop, the exact scenario a stop exists for.
- **Example:** Stop $125, limit $124 — if price gaps to $120 it won't sell, leaving you holding.
- **Common mistake:** Using stop-limits for protection without accepting the no-fill risk.

### C.5 Trailing stop
- **What it is:** A stop that follows price by a fixed $ or % as the trade moves your way.
- **The logic / why:** Lets winners run while ratcheting risk down; you give back the trail distance at the end.
- **Example:** NVDA $130, trail $5 → rises to $140, stop trails to $135; a drop to $135 exits.
- **Common mistake:** Trailing too tight — normal noise shakes you out.

### C.6 Bracket order
- **What it is:** Entry + profit target + stop-loss submitted together, linked as OCA (one-cancels-all).
- **The logic / why:** Pre-commits your whole trade — risk *and* reward — while you're calm, before you're in it.
- **On the iPad:** Attach a take-profit and stop to your entry so all three go in at once.
- **Example:** Buy MSFT $450, target $470, stop $440 — if either exit fills, the other auto-cancels.
- **Drill:** Place 3 bracket trades; confirm OCA cancels the sibling when one fills.
- **Common mistake:** Widening the stop after entry. Tighten only — never give a loser "more room."

---

## Part D — Order Settings & Execution

### D.1 Time in Force: DAY vs GTC   🎓
> **🎓 Also in CFA L1 — Equity 6.1** (order validity instructions)
- **What it is:** How long an order lives. DAY dies at the close; GTC ("good-till-cancelled") persists.
- **The logic / why:** Match the order's life to the *reason* behind it — intraday reasons shouldn't survive overnight.
- **Common mistake:** A forgotten GTC order firing days later.

### D.2 SMART routing   🎓
> **🎓 Also in CFA L1 — Equity 6.1** (execution / market structure)
- **What it is:** IBKR automatically routes to the best available price/venue. Leave it on.

### D.3 Order status lifecycle
- **What it is:** submitted → working → filled (or partial / cancelled).
- **Drill:** Watch an unfilled limit sit as "working," then modify its price and watch it update.

---

## Part E — Positions, Leverage & Margin

### E.1 Long vs. short   🎓
> **🎓 Also in CFA L1 — Equity 6.1** (long/short positions)
- **What it is:** Long = profit if price rises; short = borrow-and-sell, profit if price falls.
- **The logic / why:** Shorting has asymmetric risk (losses are unbounded as price rises). Start long-only.

### E.2 Leverage & margin   🎓
> **🎓 Also in CFA L1 — Equity 6.1** (leverage, margin, margin call) · **Corporate Issuers 5.6** (leverage concept)
- **What it is:** Borrowing to control more than your cash; a margin call forces you to add funds or close.
- **The logic / why:** Leverage multiplies both gains *and* losses — the fastest way to blow up an account.
- **Common mistake:** Using margin before your process is proven. Trade unleveraged while learning.

---

## Part F — Risk & Position Sizing (the heart)

### F.1 Risk-per-trade & position sizing   🎓
> **🎓 Also in CFA L1 — Quant Methods (Topic 2)** (expected value, probability) · **Portfolio Mgmt (Topic 10)** (risk/return)
- **What it is:** Decide max loss per trade first (0.5–1% of account), then size from your stop.
- **The logic / why:** Size is an *output* of your stop, not a feeling: **shares = risk budget ÷ stop distance**.
- **Example:** $10,000 account, risk 1% = $100. Stop distance $10/share → 100 ÷ 10 = **10 shares**.
- **Drill:** Before every entry, write the risk in dollars and compute shares from the formula.
- **Common mistake:** Picking a share count first, then hoping the stop "feels right."

### F.2 R-multiples & expectancy   🎓
> **🎓 Also in CFA L1 — Quant Methods (Topic 2)** (expected value) · **Portfolio Mgmt (Topic 10)**
- **What it is:** 1R = your planned loss. Measure every result in R. Expectancy = (win% × avg win) − (loss% × avg loss).
- **The logic / why:** Detaches you from dollars and tells you whether the *system* wins over many trades. At 1:2 reward you can win only ~40% and still profit.
- **Drill:** Log each trade's R; after 20 trades compute your expectancy.

### F.3 Correlation & total risk   🎓
> **🎓 Also in CFA L1 — Portfolio Mgmt (Topic 10)** (correlation, covariance, diversification)
- **What it is:** Holding SPY + MSFT + NVDA is *not* three independent bets — they move together.
- **The logic / why:** Correlated positions stack your real risk; cap total R on the table at once.
- **Common mistake:** Thinking 5 tech longs = diversified. They're nearly one big bet.

---

## Part G — Managing an Open Trade

### G.1 Immediate protective stop
- **The logic / why:** Never hold a position without a stop attached — decide the exit before emotion arrives.
- **Drill:** Place the stop within seconds of every fill.

### G.2 Breakeven stop, trailing, scaling out
- **Breakeven:** Once profitable, slide the stop to your entry (worst case ≈ $0).
- **Trailing:** Let a winner run with a trailing stop (see C.5).
- **Scaling out:** Sell part, let the rest run — locks gains while staying in.
- **Common mistake:** Moving to breakeven too early and getting scratched out of good trades.

---

## Part H — Broker Rules & Constraints

### H.1 PDT (Pattern Day Trader) rule
- **What it is:** US **margin** account under **$25,000** → max **3 day-trades per 5 business days**.
- **The logic / why:** Shapes practice toward selectivity; paper won't trip it, but build the habit now.

### H.2 Overnight gap risk   🎓
> **🎓 Also in CFA L1 — Equity 6.1** (market mechanics)
- **What it is:** Price can jump between close and open, skipping past your stop.
- **Example:** Stop $125, bad news opens NVDA at $118 → you sell at $118, not $125.

### H.3 Market data: real-time vs delayed
- **What it is:** Without a data subscription, quotes lag ~15 min — dangerous for active trading.

---

## Part I — Context: What You're Trading

### I.1 Security market indexes (SPY)   🎓
> **🎓 Also in CFA L1 — Equity 6.2 *Security Market Indexes***
- **What it is:** SPY tracks the S&P 500 — a market-cap-weighted index.
- **The logic / why:** Trading SPY = trading the whole market's direction; know what's inside it.

### I.2 What a share is   🎓
> **🎓 Also in CFA L1 — Equity 6.4 *Overview of Equity Securities***
- **What it is:** A share = fractional ownership (usually common stock, with voting rights).

---

## Part J — Process & Psychology

### J.1 Trade journal
- **The logic / why:** Your only honest feedback loop. Log: date, ticker, in, stop, target, shares, risk (1R=$), out, result (R), lesson.

### J.2 Daily loss limit & tilt
- **The logic / why:** Decision quality collapses after losses (revenge trading). Stop for the day at −2R.

### J.3 Why edges are hard   🎓
> **🎓 Also in CFA L1 — Equity 6.3 *Market Efficiency*** (EMH, behavioral finance)
- **What it is:** Markets are largely efficient; random entries lose to costs.
- **The logic / why:** Understand *why* an edge is rare so you respect risk and don't over-trade.

---

## Quick reference — every 🎓 CFA overlap in this doc

| Trader concept | CFA L1 lesson |
|---|---|
| Bid/ask, spread, liquidity, slippage, routing, gap risk | Equity 6.1 Market Organization & Structure |
| Market / limit / stop orders, TIF | Equity 6.1 Market Organization & Structure |
| Long/short, leverage, margin | Equity 6.1 (+ Corporate Issuers 5.6) |
| Risk-per-trade, position sizing, R-multiples, expectancy | Quant Methods (Topic 2) + Portfolio Mgmt (Topic 10) |
| Correlation, total portfolio risk | Portfolio Mgmt (Topic 10) |
| SPY / index construction | Equity 6.2 Security Market Indexes |
| What a share is | Equity 6.4 Overview of Equity Securities |
| Why edges are hard | Equity 6.3 Market Efficiency |

*Takeaway: the trading mechanics in Parts B–E and the risk logic in Part F are where trading practice and CFA study reinforce each other most. Master those first.*

---

## Trade journal template
```
Date | Ticker | In | Stop | Target | Shares | Risk (1R=$) | Out | Result (R) | Lesson
```
