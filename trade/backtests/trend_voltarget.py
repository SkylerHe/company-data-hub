#!/usr/bin/env python3
"""S3 Phase-3 — Trend following with VOLATILITY TARGETING (the lever to higher return).

Upgrades the basic S3 (trend_backtest.py) three ways (see ../TREND_FOLLOWING_PLAN.md):
  1. MULTI-SPEED signal — average the (price > SMA) trend filter across 50/100/200-day
     lookbacks → a 0..1 conviction per asset (smoother, less whipsaw than a single MA).
  2. VOLATILITY TARGETING — scale the whole book's leverage each month so its realized
     vol tracks a chosen target. This is HOW a CTA turns a low-vol base into higher return.
  3. Honest frictions — transaction costs on turnover + financing cost on borrowed leverage.

Sweeps target vol (10/15/20%) so you see the return↔drawdown trade-off, and what leverage
it actually takes to chase ~15%/yr. Standalone (yfinance + pandas).
Run: source venv/bin/activate && python trade/backtests/trend_voltarget.py
"""
import numpy as np
import pandas as pd
import yfinance as yf

ASSETS = ["SPY", "QQQ", "EFA", "EEM", "TLT", "GLD", "DBC", "UUP"]
START = "2007-01-01"
LOOKBACKS = [50, 100, 200]        # multi-speed trend filters
VOL_WIN = 60                      # trailing window for asset & portfolio vol
RF = 0.04; RF_DAILY = 1.04 ** (1 / 252) - 1
FIN = 0.05; FIN_DAILY = 1.05 ** (1 / 252) - 1   # borrowing rate on leverage (RF + 1% spread)
MAX_LEV = 3.0
COST_BPS = 0.0010                 # 10 bps of traded notional per unit turnover


def load_prices():
    data = {}
    for t in ASSETS:
        h = yf.Ticker(t).history(start=START, auto_adjust=True)["Close"]
        if h is not None and len(h):
            data[t] = h
    px = pd.DataFrame(data).dropna()
    px.index = px.index.tz_localize(None)
    return px


def stats(r: pd.Series):
    eq = (1 + r).cumprod()
    years = (r.index[-1] - r.index[0]).days / 365.25
    return (eq.iloc[-1] ** (1 / years) - 1, r.std() * np.sqrt(252),
            (r.mean() - RF_DAILY) / r.std() * np.sqrt(252), (eq / eq.cummax() - 1).min())


def base_strategy(px):
    """Unlevered multi-speed trend. Returns per-day (risky_ret, invested) + monthly weights."""
    rets = px.pct_change().fillna(0.0)
    smas = {k: px.rolling(k).mean() for k in LOOKBACKS}
    vol = rets.rolling(VOL_WIN).std() * np.sqrt(252)
    dates = px.index
    w = pd.Series(0.0, index=px.columns); cur = None
    rows = []; wmat = {}
    for i in range(max(LOOKBACKS) + 1, len(dates)):
        d = dates[i]
        if d.to_period("M") != cur:
            cur = d.to_period("M")
            conv = sum((px.iloc[i - 1] > smas[k].iloc[i - 1]).astype(float) for k in LOOKBACKS) / len(LOOKBACKS)
            iv = (1.0 / vol.iloc[i - 1]).replace([np.inf, -np.inf], np.nan).fillna(0.0)
            raw = conv * iv
            denom = iv.sum()
            w = raw / denom if denom > 0 else raw * 0.0
        risky = float((w * rets.iloc[i]).sum()); invested = float(w.sum())
        rows.append((d, risky, invested, risky + (1 - invested) * RF_DAILY))
        wmat[d] = w.copy()
    df = pd.DataFrame(rows, columns=["date", "risky", "invested", "base_ret"]).set_index("date")
    return df, wmat


def vol_target(df, wmat, target):
    """Scale leverage monthly so realized vol ~ target; apply financing + transaction costs."""
    rv = df["base_ret"].rolling(VOL_WIN).std() * np.sqrt(252)
    prev_lw = pd.Series(0.0, index=wmat[df.index[0]].index)
    cur = None; L = 1.0; out = []; levs = []
    for d in df.index:
        tc = 0.0
        if d.to_period("M") != cur:
            cur = d.to_period("M")
            rvol = rv.shift(1).get(d, np.nan)
            L = float(np.clip(target / rvol, 0.0, MAX_LEV)) if rvol and rvol > 0 else 0.0
            new_lw = L * wmat[d]
            tc = COST_BPS * float((new_lw - prev_lw).abs().sum())
            prev_lw = new_lw
        risky = df.at[d, "risky"]; invested = df.at[d, "invested"]
        net_cash = 1 - L * invested
        rate = RF_DAILY if net_cash >= 0 else FIN_DAILY
        out.append((d, L * risky + net_cash * rate - tc)); levs.append(L)
    return pd.Series([r for _, r in out], index=[d for d, _ in out]), float(np.mean(levs))


def main():
    px = load_prices()
    df, wmat = base_strategy(px)
    print(f"\n{'='*82}")
    print(f"S3 Phase-3 — Vol-targeted trend (multi-speed 50/100/200, costs+financing)")
    print(f"{df.index[0].date()} → {df.index[-1].date()}  ·  {len(px.columns)} ETFs  ·  max lev {MAX_LEV}x, borrow @{FIN:.0%}")
    print(f"{'='*82}")
    print(f"{'Version':<28}{'CAGR':>8}{'Vol':>8}{'Sharpe':>9}{'Max DD':>9}{'Avg lev':>9}")

    c, v, sh, dd = stats(df["base_ret"])
    print(f"{'Base (no vol target)':<28}{c:>7.1%}{v:>8.1%}{sh:>8.2f}{dd:>9.1%}{1.0:>9.2f}")
    for tgt in [0.10, 0.15, 0.20]:
        r, avglev = vol_target(df, wmat, tgt)
        c, v, sh, dd = stats(r)
        print(f"{'Vol-target ' + f'{tgt:.0%}':<28}{c:>7.1%}{v:>8.1%}{sh:>8.2f}{dd:>9.1%}{avglev:>9.2f}")

    print(f"\n  Read: vol-targeting scales RETURN with leverage while ~preserving Sharpe —")
    print(f"  so chasing ~15% return means accepting a deeper drawdown. That's the honest trade.")


if __name__ == "__main__":
    main()
