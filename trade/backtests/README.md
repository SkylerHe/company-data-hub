# Backtests

Runnable code behind the strategies in [`../STRATEGY_RESEARCH.md`](../STRATEGY_RESEARCH.md).
Kept in the repo (not scratchpad) so results are **reproducible**.

Run from the repo root with the venv active:
```bash
source venv/bin/activate
python trade/backtests/dip_backtest.py    # single-window pass (uses finance.db: QQQ, SPY)
python trade/backtests/dip_rigorous.py    # rolling 5-yr windows (pulls ~25y SPY/QQQ via yfinance)
```

## Scripts
- **`dip_backtest.py`** — S1 dip-buying (fixed vs relative levels) vs buy-and-hold over ONE
  window from `finance.db`. Illustrative only — a single path proves nothing.
- **`dip_rigorous.py`** — S1 over **259 rolling 5-yr windows** (~25y history via yfinance),
  reporting the distribution: median/mean return, Sharpe, max drawdown, and win-rate vs
  buy-and-hold. Undeployed cash earns 4%/yr. *This* is the honest test.
- **`dca_dip_backtest.py`** — **S2**: a *monthly income stream* ($50k/mo) into QQQ,
  2005→today. Base DCA + dip reserve + a cash-cap sweep (K = 1/2/3/6 months) vs pure DCA.
  Reports **IRR** (money-weighted annual return) + max drawdown. Standalone (yfinance).

## Reminder (the whole point)
A strategy that wins one backtest means nothing. Judge on the **distribution** across many
windows, on **risk-adjusted** terms (Sharpe + drawdown), and check **assumption sensitivity**
before trusting anything. See the methodology principles at the top of `STRATEGY_RESEARCH.md`.
