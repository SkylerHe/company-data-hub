#!/usr/bin/env python3
"""S2 — Monthly-contribution DCA + dip-buying on QQQ (2005 -> today).

The real-life question (unlike S1's lump sum): $50k arrives EVERY MONTH. How do
you deploy an ongoing income stream? This tests one rule against pure auto-invest:

  * BASE DCA  — buy a fixed slice of each paycheck immediately (always in market),
  * DIP overlay — hold the rest as reserve, deploy an extra tranche when QQQ falls
                  from its running peak (-10%, -20%; each fires once per drawdown),
  * CASH CAP  — never let idle reserve exceed K months of pay; deploy the excess
                (this is the "cash piled up -> raise the DCA" rule, made mechanical).

Benchmark: PURE DCA — 100% of every paycheck into QQQ the day it arrives.

Reports money-weighted annual return (IRR) + max drawdown for the benchmark and
for cash caps K = 1/2/3/6 months. Undeployed cash earns 4%/yr (T-bill-ish).

Why IRR, not (final/contributed): with money arriving monthly, a dollar from 2005
compounded ~20 yrs, one from last month ~0. IRR weights each dollar by time invested.

Standalone (no finance.db) — needs numpy + yfinance from the venv.
Run:  source venv/bin/activate && python trade/backtests/dca_dip_backtest.py
"""
import numpy as np
import yfinance as yf

CONTRIB    = 50_000.0             # cash arriving at the start of each month
BASE_FRAC  = 0.50                 # fraction of each paycheck bought immediately (base DCA)
DIP_LEVELS = [0.10, 0.20]         # deploy a reserve tranche at -10% / -20% from running peak
DIP_TRANCHE = CONTRIB            # dollars deployed per dip level (one paycheck), capped by reserve
RF_DAILY   = 1.04 ** (1 / 252) - 1   # 4%/yr on idle cash, compounded daily
START      = "2005-01-01"


def load_qqq():
    df = yf.Ticker("QQQ").history(start=START, auto_adjust=True)
    px = df["Close"].to_numpy()
    dates = df.index
    ym = np.array([d.year * 12 + d.month for d in dates])   # year-month key
    is_month_start = np.empty(len(dates), bool)
    is_month_start[0] = True
    is_month_start[1:] = ym[1:] != ym[:-1]                  # first trading day of each month
    years = np.array([(d - dates[0]).days / 365.25 for d in dates])
    return px, is_month_start, years, dates


def run(px, is_month_start, mode, cap_months=None):
    """mode 'dca' = pure benchmark; 's2' = base DCA + dip overlay + cash cap.
    Returns (value_path, contribution_cashflows, n_dip_buys, avg_idle_cash)."""
    n = len(px)
    cash = 0.0; shares = 0.0; val = np.empty(n)
    cashflows = []                          # (day_index, amount); contributions are negative
    peak = px[0]; fired = [False] * len(DIP_LEVELS)
    n_dip = 0; cash_sum = 0.0
    cap = (cap_months or 0) * CONTRIB
    for t in range(n):
        cash *= (1 + RF_DAILY)              # idle cash earns 4%/yr
        p = px[t]
        if is_month_start[t]:
            cash += CONTRIB
            cashflows.append((t, -CONTRIB))
            if mode == "dca":
                shares += cash / p; cash = 0.0            # deploy the whole paycheck now
            else:
                buy = min(cash, BASE_FRAC * CONTRIB)      # base DCA: fixed slice now
                shares += buy / p; cash -= buy
        if mode == "s2":
            if p >= peak:                                 # new high -> reset the dip ladder
                peak = p; fired = [False] * len(DIP_LEVELS)
            for i, lv in enumerate(DIP_LEVELS):           # dip buys from reserve
                if not fired[i] and p <= peak * (1 - lv):
                    buy = min(cash, DIP_TRANCHE)
                    if buy > 0:
                        shares += buy / p; cash -= buy; n_dip += 1
                    fired[i] = True
            if cap and cash > cap:                        # cash cap: deploy idle excess
                excess = cash - cap
                shares += excess / p; cash -= excess
        cash_sum += cash
        val[t] = cash + shares * p
    return val, cashflows, n_dip, cash_sum / n


def xirr_annual(cashflows, years, final_value):
    """Money-weighted annual return: rate r s.t. discounted contributions + final = 0."""
    flows = [(years[t], amt) for t, amt in cashflows]
    flows.append((years[-1], final_value))
    npv = lambda r: sum(cf / (1 + r) ** ty for ty, cf in flows)
    lo, hi = -0.9999, 100.0                               # npv is monotone decreasing in r
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(mid) > 0: lo = mid
        else: hi = mid
    return (lo + hi) / 2


def max_drawdown(val):
    peak = np.maximum.accumulate(val)
    return ((val - peak) / peak).min()


def main():
    px, ims, years, dates = load_qqq()
    n_months = int(ims.sum()); total = n_months * CONTRIB
    print(f"\n{'='*76}")
    print(f"S2 - QQQ  {dates[0].date()} -> {dates[-1].date()}  "
          f"({len(px)} days, {n_months} monthly contributions)")
    print(f"${CONTRIB:,.0f}/mo · total in ${total/1e6:.2f}M · base DCA {BASE_FRAC:.0%} · "
          f"dips {[f'-{int(l*100)}%' for l in DIP_LEVELS]} · idle cash @4%")
    print(f"{'='*76}")
    print(f"{'Strategy':<20}{'Final $':>14}{'IRR/yr':>9}{'Max DD':>9}"
          f"{'Dip buys':>10}{'Avg idle$':>12}")

    val, cf, ndip, avgc = run(px, ims, "dca")
    print(f"{'Pure DCA (100%)':<20}{val[-1]:>14,.0f}{xirr_annual(cf, years, val[-1]):>8.1%}"
          f"{max_drawdown(val):>9.1%}{ndip:>10}{avgc:>12,.0f}")
    for k in [1, 2, 3, 6]:
        val, cf, ndip, avgc = run(px, ims, "s2", cap_months=k)
        print(f"{'S2 cap=' + str(k) + 'mo':<20}{val[-1]:>14,.0f}{xirr_annual(cf, years, val[-1]):>8.1%}"
              f"{max_drawdown(val):>9.1%}{ndip:>10}{avgc:>12,.0f}")

    print(f"\n  IRR    = money-weighted annual return (each $ weighted by time invested).")
    print(f"  Max DD = worst peak-to-trough on TOTAL account value; cushioned by the ongoing")
    print(f"           contributions, so it reads milder than a lump-sum drawdown would.")


if __name__ == "__main__":
    main()
