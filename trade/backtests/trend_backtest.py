#!/usr/bin/env python3
"""S3 — Basic trend-following (CTA) on a cross-asset ETF basket.

Phase-2 version (see ../TREND_FOLLOWING_PLAN.md): the simplest honest trend system.
  * Universe: a diversified ETF basket (equities, bonds, gold, commodities, USD, intl).
  * Signal:   hold an asset only while its price is ABOVE its 200-day moving average
              (a classic trend filter); otherwise that sleeve sits in cash.
  * Sizing:   inverse-volatility (risk parity) across the assets currently in-trend —
              jumpier markets get smaller weight so each contributes ~equal risk.
  * Rebalance monthly. Undeployed weight earns cash at 4%/yr.

Reports CAGR, annualized vol, Sharpe (rf=4%), and max drawdown, vs two benchmarks
(buy-&-hold SPY, and buy-&-hold the equal-weight basket) — to see the classic trend
trade-off: similar/modest return but MUCH smaller drawdown ("crisis alpha").

Standalone (yfinance + pandas). Run: source venv/bin/activate && python trade/backtests/trend_backtest.py
"""
import numpy as np
import pandas as pd
import yfinance as yf

ASSETS = {                       # ticker: asset class (diversification is the real edge)
    "SPY": "US equity", "QQQ": "US tech", "EFA": "Intl developed", "EEM": "EM equity",
    "TLT": "Long bonds", "GLD": "Gold", "DBC": "Commodities", "UUP": "US dollar",
}
START = "2007-01-01"             # common history where all 8 ETFs exist
MA_WIN = 200                     # trend filter: price vs 200-day SMA
VOL_WIN = 60                     # trailing window for volatility sizing
RF = 0.04                        # cash yield on undeployed weight
RF_DAILY = 1.04 ** (1 / 252) - 1


def load_prices():
    data = {}
    for t in ASSETS:
        h = yf.Ticker(t).history(start=START, auto_adjust=True)["Close"]
        if h is not None and len(h):
            data[t] = h
    px = pd.DataFrame(data).dropna()          # common trading dates across all assets
    px.index = px.index.tz_localize(None)
    return px


def stats(daily_ret: pd.Series):
    """(CAGR, ann vol, Sharpe@rf, max drawdown) from a daily-return series."""
    eq = (1 + daily_ret).cumprod()
    years = (daily_ret.index[-1] - daily_ret.index[0]).days / 365.25
    cagr = eq.iloc[-1] ** (1 / years) - 1
    vol = daily_ret.std() * np.sqrt(252)
    sharpe = (daily_ret.mean() - RF_DAILY) / daily_ret.std() * np.sqrt(252)
    maxdd = (eq / eq.cummax() - 1).min()
    return cagr, vol, sharpe, maxdd


def run_trend(px):
    rets = px.pct_change().fillna(0.0)
    sma = px.rolling(MA_WIN).mean()
    vol = rets.rolling(VOL_WIN).std() * np.sqrt(252)
    dates = px.index
    w = pd.Series(0.0, index=px.columns)      # current asset weights
    cash_w = 1.0
    out = []
    cur_month = None
    for i in range(MA_WIN + 1, len(dates)):
        d = dates[i]
        if d.to_period("M") != cur_month:     # monthly rebalance, using yesterday's data
            cur_month = d.to_period("M")
            in_trend = px.iloc[i - 1] > sma.iloc[i - 1]
            inv_vol = (1.0 / vol.iloc[i - 1]).replace([np.inf, -np.inf], np.nan).fillna(0.0)
            raw = inv_vol.where(in_trend, 0.0)             # invvol if in uptrend else 0
            denom = inv_vol.sum()                           # normalize by TOTAL invvol
            w = raw / denom if denom > 0 else raw * 0.0     # out-of-trend sleeves -> cash
            cash_w = 1.0 - w.sum()
        r = float((w * rets.iloc[i]).sum() + cash_w * RF_DAILY)
        out.append((d, r))
    return pd.Series([r for _, r in out], index=[d for d, _ in out])


def main():
    px = load_prices()
    print(f"\n{'='*74}")
    print(f"S3 — Trend following (200-day MA, inverse-vol) on {len(px.columns)} ETFs")
    print(f"{px.index[0].date()} → {px.index[-1].date()}  ·  basket: {', '.join(px.columns)}")
    print(f"{'='*74}")

    rets = px.pct_change().fillna(0.0)
    strat = run_trend(px)
    common = strat.index
    spy = rets["SPY"].reindex(common)
    basket = rets.mean(axis=1).reindex(common)          # equal-weight buy & hold

    print(f"{'Strategy':<28}{'CAGR':>8}{'Vol':>8}{'Sharpe':>9}{'Max DD':>9}")
    for name, r in [("Trend (S3)", strat),
                    ("Buy & hold SPY", spy),
                    ("Buy & hold basket (EW)", basket)]:
        c, v, sh, dd = stats(r)
        print(f"{name:<28}{c:>7.1%}{v:>8.1%}{sh:>8.2f}{dd:>9.1%}")

    # crisis alpha check: worst calendar years
    print("\n  Crisis check — return in the ugly years (trend should cushion):")
    for yr in [2008, 2018, 2020, 2022]:
        s = strat[strat.index.year == yr]
        b = spy[spy.index.year == yr]
        if len(s) and len(b):
            print(f"    {yr}:  Trend {(1+s).prod()-1:>7.1%}   |   SPY {(1+b).prod()-1:>7.1%}")

    print("\n  Note: Phase-2 basic version. Sharpe/return are the HONEST first read —")
    print("  next (Phase 3): multi-speed signals, vol-targeting, costs; (Phase 4): rolling windows.")


if __name__ == "__main__":
    main()
