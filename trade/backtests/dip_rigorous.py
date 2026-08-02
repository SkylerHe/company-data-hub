#!/usr/bin/env python3
"""Rigorous rolling-window backtest: dip-buying (fixed & relative) vs buy-and-hold.

Pulls ~25 yrs of SPY & QQQ from yfinance (adjusted close = total return), runs the
strategy over ROLLING 5-yr windows (monthly starts) and reports the DISTRIBUTION of
outcomes — total return, annualized Sharpe (rf=0 in ratio), max drawdown, and how
often dip-buying beats buy-and-hold. Undeployed cash earns 4%/yr (compounded daily).

This is the "many-window" test that keeps you from being fooled by one lucky path.
Standalone (no finance.db) — needs numpy + yfinance from the venv.

Run:  source venv/bin/activate && python trade/backtests/dip_rigorous.py
"""
import numpy as np
import yfinance as yf

BUDGET = 30_000.0
TRANCHE = BUDGET / 3
LEVELS = [0.05, 0.10, 0.15]
WIN = 252 * 5          # 5-year window (trading days)
STEP = 21             # start a new window every ~month
RF_DAILY = 1.04 ** (1 / 252) - 1   # 4%/yr on undeployed cash, compounded daily


def run(prices, mode):
    """prices: np array of daily closes for one window. Returns the value-path array."""
    n = len(prices); cash = BUDGET; shares = 0.0; val = np.empty(n)
    if mode == "hold":
        return (BUDGET / prices[0]) * prices
    fired = [False, False, False]
    levels = [prices[0] * (1 - l) for l in LEVELS] if mode == "fixed" else None
    high = prices[0]
    for t in range(n):
        cash *= (1 + RF_DAILY)          # undeployed cash earns 4%/yr
        p = prices[t]
        if mode == "relative":
            high = max(high, p)
        for i in range(3):
            if fired[i]:
                continue
            trig = (p <= levels[i]) if mode == "fixed" else (p / high - 1 <= -LEVELS[i])
            if trig:
                shares += TRANCHE / p; cash -= TRANCHE; fired[i] = True
        val[t] = cash + shares * p
    return val


def metrics(val):
    total_ret = val[-1] / BUDGET - 1
    daily = np.diff(val) / val[:-1]
    sd = daily.std()
    sharpe = (daily.mean() / sd * np.sqrt(252)) if sd > 1e-12 else 0.0
    peak = np.maximum.accumulate(val)
    maxdd = ((val - peak) / peak).min()
    return total_ret, sharpe, maxdd


def main():
    for tkr in ["SPY", "QQQ"]:
        df = yf.Ticker(tkr).history(start="2000-01-01", auto_adjust=True)
        px = df["Close"].to_numpy()
        d = df.index
        print(f"\n{'='*78}\n{tkr}: {len(px)} days, {d[0].date()} → {d[-1].date()}\n{'='*78}")
        starts = list(range(0, len(px) - WIN, STEP))
        agg = {m: {"ret": [], "sharpe": [], "dd": []} for m in ["hold", "fixed", "relative"]}
        beat_fixed = beat_rel = 0
        for s in starts:
            w = px[s:s + WIN]
            res = {}
            for m in ["hold", "fixed", "relative"]:
                tr, sh, dd = metrics(run(w, m))
                agg[m]["ret"].append(tr); agg[m]["sharpe"].append(sh); agg[m]["dd"].append(dd)
                res[m] = tr
            beat_fixed += res["fixed"] > res["hold"]
            beat_rel += res["relative"] > res["hold"]
        N = len(starts)
        print(f"{N} rolling 5-yr windows (undeployed cash @ 4%/yr)\n")
        print(f"{'Strategy':<26}{'Median ret':>11}{'Mean ret':>10}{'Med Sharpe':>12}"
              f"{'Med maxDD':>11}{'Worst ret':>11}")
        for m, label in [("hold", "Buy & hold"), ("fixed", "Fixed-dollar dips"),
                         ("relative", "Relative dips")]:
            a = agg[m]
            print(f"{label:<26}{np.median(a['ret']):>10.1%}{np.mean(a['ret']):>10.1%}"
                  f"{np.median(a['sharpe']):>12.2f}{np.median(a['dd']):>11.1%}{min(a['ret']):>11.1%}")
        print(f"\n  Dip-buying beat buy-and-hold:  fixed {beat_fixed}/{N} ({beat_fixed/N:.0%})  |  "
              f"relative {beat_rel}/{N} ({beat_rel/N:.0%})")


if __name__ == "__main__":
    main()
