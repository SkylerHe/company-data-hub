#!/usr/bin/env python3
"""Dip-buying single-window backtest (fixed vs relative levels) vs buy-and-hold.

Uses the local finance.db price history (QQQ, SPY). This is the ILLUSTRATIVE
single-path pass — good for seeing the mechanics and buy dates, but a single
window proves nothing (see dip_rigorous.py for the rolling many-window version).

Budget $30k, 3 tranches of $10k, each fires once, hold to end, undeployed cash 0%.

Run:  source venv/bin/activate && python trade/backtests/dip_backtest.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
os.chdir(REPO)  # store.DB_PATH is CWD-relative ("finance.db")
import store  # noqa: E402

BUDGET = 30_000
TRANCHE = BUDGET / 3
LEVELS = [0.05, 0.10, 0.15]  # -5%, -10%, -15%


def prices(tkr):
    db = store.get_db()
    iid = db.execute("SELECT id FROM instruments WHERE ticker=?", (tkr,)).fetchone()[0]
    return db.execute(
        "SELECT date, close FROM prices WHERE instrument_id=? AND close IS NOT NULL "
        "ORDER BY date", (iid,)).fetchall()


def buy_and_hold(px):
    d0, p0 = px[0]; pN = px[-1][1]
    shares = BUDGET / p0
    final = shares * pN
    return dict(name="Buy & hold", deployed=BUDGET, cash=0, shares=shares,
                avg_cost=p0, final=final, ret=final / BUDGET - 1, buys=[(d0, round(p0, 2))])


def fixed_dips(px):
    p0 = px[0][1]
    levels = [p0 * (1 - l) for l in LEVELS]  # fixed dollar levels below day-1 price
    fired = [False] * len(levels); cash = BUDGET; shares = 0.0; buys = []
    for d, p in px:
        for i, lv in enumerate(levels):
            if not fired[i] and p <= lv:
                shares += TRANCHE / p; cash -= TRANCHE; fired[i] = True; buys.append((d, round(p, 2)))
    pN = px[-1][1]; deployed = BUDGET - cash
    final = shares * pN + cash
    return dict(name="Fixed-dollar dips", deployed=deployed, cash=cash, shares=shares,
                avg_cost=(deployed / shares if shares else 0), final=final,
                ret=final / BUDGET - 1, buys=buys)


def relative_dips(px):
    high = px[0][1]; fired = [False] * len(LEVELS); cash = BUDGET; shares = 0.0; buys = []
    for d, p in px:
        high = max(high, p)
        dd = p / high - 1
        for i, l in enumerate(LEVELS):
            if not fired[i] and dd <= -l:
                shares += TRANCHE / p; cash -= TRANCHE; fired[i] = True; buys.append((d, round(p, 2)))
    pN = px[-1][1]; deployed = BUDGET - cash
    final = shares * pN + cash
    return dict(name="Relative dips (from peak)", deployed=deployed, cash=cash, shares=shares,
                avg_cost=(deployed / shares if shares else 0), final=final,
                ret=final / BUDGET - 1, buys=buys)


def main():
    for tkr in ["QQQ", "SPY"]:
        px = prices(tkr)
        print(f"\n{'='*70}\n{tkr}  ({px[0][0]} → {px[-1][0]}, start ${px[0][1]:.2f}, "
              f"end ${px[-1][1]:.2f}, {px[-1][1]/px[0][1]-1:+.0%})\n{'='*70}")
        print(f"{'Strategy':<26}{'Deployed':>10}{'Cash left':>10}{'Final $':>11}{'Return':>9}{'Avg cost':>10}")
        for fn in (buy_and_hold, fixed_dips, relative_dips):
            r = fn(px)
            print(f"{r['name']:<26}{r['deployed']:>9,.0f}{r['cash']:>10,.0f}{r['final']:>11,.0f}"
                  f"{r['ret']:>8.1%}{r['avg_cost']:>10.2f}")
        for fn in (fixed_dips, relative_dips):
            r = fn(px)
            b = ", ".join(f"{d}@${p}" for d, p in r['buys']) or "never triggered"
            print(f"   {r['name']} buys: {b}")


if __name__ == "__main__":
    main()
