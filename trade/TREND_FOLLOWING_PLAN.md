# Trend Following / CTA — Build Plan 🧭

My path to a **systematic trend-following strategy** I can eventually run on my own
capital (milestone: a **$1M account**; long-term: **~$15M, solo, not high-frequency,
low-maintenance**). Complements [`STRATEGY_RESEARCH.md`](STRATEGY_RESEARCH.md) (where the
actual backtests get logged as S# entries) and the reading list in the `papers` table.

## ⚠️ Honest expectation on returns (read first)
Pure trend following does **not** reliably return 15%/yr. Realistic: **Sharpe ~0.5–0.8**,
returns ~6–12% at typical vol, with the real value being **"crisis alpha"** (shines in
crashes). 15% is a *stretch* needing **diversification + vol-targeting + modest cheap
leverage (futures)** — not a base case. **Rule: build honestly, measure the real
return/Sharpe/drawdown, THEN decide how to reach the target. Never fit the strategy to hit
a number** (the S1 overfitting lesson).

## Why trend following (fits the solo goal)
Liquid markets · long holding periods · **self-automating → low-maintenance** · durable
edge (a century of evidence) · works small AND large · fully **published** (so I can build
it myself — unlike stat arb, where the edge is proprietary infrastructure).

## Resources (reliable)
**Papers** (in the `papers` table):
- Moskowitz, Ooi, Pedersen (2012), *Time Series Momentum* — foundational.
- Hurst, Ooi, Pedersen, *A Century of Evidence on Trend-Following Investing* (AQR).
- Hurst, Ooi, Pedersen, *Demystifying Managed Futures* (AQR) — how CTAs construct it.

**Books:** Andreas Clenow, *Following the Trend* (the blueprint) · Ernie Chan,
*Algorithmic Trading* (backtesting discipline) · Perry Kaufman, *Trading Systems and
Methods* (reference).

**Data:** `finance.db` (ETF prices + `ma_20/50/200`) → free `yfinance` cross-asset ETF
basket (SPY, TLT, GLD, DBC, UUP, EFA, EEM, QQQ). Benchmark vs the SG Trend Index. Real
futures data (IBKR/vendor) only later.

## The 5 concepts to master
1. **Trend signal** (price vs moving average / 12-mo return)
2. **Volatility position-sizing** (smaller size in jumpier markets → equal risk each)
3. **Diversification across many markets** (the real edge)
4. **Volatility targeting** (scale the whole book to a target risk)
5. **Payoff profile** (crisis alpha, moderate Sharpe, big diversification benefit)

## Phased plan
- **Phase 1 — Learn** (~1–2 wks, $0): 2 core papers + Clenow ch. 1–5; nail the 5 concepts.
- **Phase 2 — Basic backtest (S3)** ← *starting now*: trend on the ETF basket using the MAs,
  inverse-vol sizing, cash when out of trend; rolling metrics (CAGR, Sharpe, max DD) vs
  buy-and-hold. Reuse `dip_rigorous.py` machinery.
- **Phase 3 — Real CTA:** multi-speed signals (fast+slow), volatility targeting,
  transaction costs, more markets.
- **Phase 4 — Validate rigorously:** rolling windows, out-of-sample, assumption
  sensitivity → the *honest* expected return/Sharpe/DD. Only then decide on leverage.
- **Phase 5 — Paper trade** (IBKR): forward-test for months (backtest → paper → live).
- **Phase 6 — Small live → scale:** track record → grow toward $1M → $15M.

**Guiding principle:** the edge is *disciplined implementation and testing*, not optimism.
The strategy tells me its return — I don't tell it.
