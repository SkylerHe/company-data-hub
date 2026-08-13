#!/usr/bin/env python3
"""
option_strategy.py — option strategy P&L: max profit / max loss / break-even (read-only).

Turns a strategy + its strikes/premiums into the numbers a broker ticket shows —
max profit, max loss, break-even(s), where the upside is capped — plus a payoff
table across a range of underlying prices at EXPIRATION, and a plain-English read.

Covers the exact structures we discussed on QQQ:
    covered_call    own shares, SELL a call            (income, tiny downside cushion)
    protective_put  own shares, BUY a put              (real downside floor)
    collar          own shares, BUY put + SELL call    (cheap capped protection)
    long_call / long_put   a single bought option      (defined risk = premium)
    short_call      a NAKED sold call                  (shows the UNLIMITED-loss case)

Premiums can be given directly (read them off the ticket) OR derived from an IV with
--iv + --days (uses volatility.bs_greeks, so it ties into the same engine).

All figures are PER SHARE and PER CONTRACT(S) (×100×--contracts). "own shares"
strategies assume 100 shares per contract at cost basis --basis (defaults to spot).

Usage:
    python option_strategy.py --strategy covered_call --spot 733.94 \
        --call-strike 748 --call-premium 2.85

    python option_strategy.py --strategy collar --spot 733.94 --basis 700 \
        --put-strike 713 --put-premium 1.23 --call-strike 754 --call-premium 1.67

    # derive premiums from IV instead of quoting them:
    python option_strategy.py --strategy protective_put --spot 733.94 \
        --put-strike 713 --iv 19.05 --days 7
"""

import argparse

import volatility

CONTRACT = 100          # shares per option contract
INF = float("inf")


def _payoff(strategy, S, spot, basis, kp, cp, kc, cc):
    """Per-share P&L of the strategy if the underlying is `S` at expiration."""
    stock = S - basis                                   # long-shares leg
    long_put = (max(kp - S, 0.0) - cp) if kp is not None else 0.0
    short_call = (cc - max(S - kc, 0.0)) if kc is not None else 0.0
    if strategy == "covered_call":
        return stock + short_call
    if strategy == "protective_put":
        return stock + long_put
    if strategy == "collar":
        return stock + long_put + short_call
    if strategy == "long_call":
        return max(S - kc, 0.0) - cc                     # kc/cc reused as the bought call
    if strategy == "long_put":
        return max(kp - S, 0.0) - cp
    if strategy == "short_call":
        return cc - max(S - kc, 0.0)
    raise ValueError(strategy)


def analyze(strategy, spot, basis, kp, cp, kc, cc, contracts):
    """Return the headline numbers by scanning payoff from 0 to a high price."""
    # Sample densely from 0 to 3× spot to find max/min and the zero-crossings.
    hi_scan = max(spot * 3, (kc or 0) * 2, (kp or 0) * 2, 1.0)
    xs = [i * hi_scan / 4000 for i in range(4001)]
    ys = [_payoff(strategy, x, spot, basis, kp, cp, kc, cc) for x in xs]

    # Unbounded-profit strategies (long call, and shares with no upside cap).
    uncapped_up = strategy in ("long_call",) or (
        strategy in ("protective_put",))                 # shares upside is open
    uncapped_down = strategy in ("short_call",)          # naked short call: infinite loss

    max_profit = INF if uncapped_up else max(ys)
    max_loss = -INF if uncapped_down else min(ys)

    # Break-evens: sign changes of the payoff curve.
    bes = []
    for i in range(1, len(xs)):
        if (ys[i - 1] <= 0 <= ys[i]) or (ys[i - 1] >= 0 >= ys[i]):
            if ys[i] != ys[i - 1]:
                t = (0 - ys[i - 1]) / (ys[i] - ys[i - 1])
                bes.append(round(xs[i - 1] + t * (xs[i] - xs[i - 1]), 2))
    # de-dupe near-identical roots
    be_clean = []
    for b in bes:
        if not be_clean or abs(b - be_clean[-1]) > 0.01:
            be_clean.append(b)

    mult = CONTRACT * contracts
    return {
        "max_profit": max_profit, "max_loss": max_loss,
        "max_profit_total": max_profit * mult if max_profit != INF else INF,
        "max_loss_total": max_loss * mult if max_loss != -INF else -INF,
        "break_evens": be_clean, "mult": mult,
    }


def _fmt(v):
    if v == INF:
        return "unlimited"
    if v == -INF:
        return "UNLIMITED (−∞)"
    return f"{v:,.2f}"


def report(strategy, spot, basis, kp, cp, kc, cc, contracts):
    a = analyze(strategy, spot, basis, kp, cp, kc, cc, contracts)
    title = strategy.replace("_", " ").title()
    print(f"\n{title}   spot {spot:g}   basis {basis:g}   "
          f"{contracts} contract(s) = {a['mult']} sh")
    legs = []
    if kp is not None:
        legs.append(f"BUY {kp:g} put @ {cp:.2f}")
    if kc is not None and strategy != "long_call":
        legs.append(f"SELL {kc:g} call @ {cc:.2f}")
    if strategy == "long_call":
        legs = [f"BUY {kc:g} call @ {cc:.2f}"]
    if strategy == "long_put":
        legs = [f"BUY {kp:g} put @ {cp:.2f}"]
    if legs:
        print("  legs: " + "   ".join(legs))

    # net premium: +credit received / −debit paid
    net = 0.0
    if strategy in ("covered_call", "short_call"):
        net = cc
    elif strategy == "protective_put":
        net = -cp
    elif strategy == "collar":
        net = cc - cp
    elif strategy == "long_call":
        net = -cc
    elif strategy == "long_put":
        net = -cp
    kind = "credit" if net >= 0 else "debit"
    print(f"  net premium: {abs(net):.2f} {kind}  ({abs(net) * a['mult']:,.2f} total)")

    print("  " + "-" * 52)
    print(f"  Max profit   {_fmt(a['max_profit']):>16}  /sh   "
          f"{_fmt(a['max_profit_total']):>14} total")
    print(f"  Max loss     {_fmt(a['max_loss']):>16}  /sh   "
          f"{_fmt(a['max_loss_total']):>14} total")
    be = ", ".join(f"{b:g}" for b in a["break_evens"]) or "—"
    print(f"  Break-even   {be:>16}")
    print("  " + "-" * 52)

    # payoff scenario table
    print("  Underlying at expiry → P&L per share (total):")
    for pct in (-0.20, -0.10, -0.05, 0.0, 0.05, 0.10, 0.20):
        S = spot * (1 + pct)
        y = _payoff(strategy, S, spot, basis, kp, cp, kc, cc)
        print(f"    {pct*100:+5.0f}%  {S:8.2f}   {y:+8.2f}   ({y * a['mult']:+,.0f})")

    # plain read on downside protection where relevant
    if strategy in ("covered_call", "protective_put", "collar"):
        cushion = (basis - a["break_evens"][0]) if a["break_evens"] else 0.0
        print("  " + "-" * 52)
        if strategy == "protective_put":
            print(f"  Real floor: below {kp:g} the put offsets every further $1 drop; "
                  f"worst case ≈ {_fmt(a['max_loss'])}/sh.")
        elif strategy == "collar":
            print(f"  Protected below {kp:g}, capped above {kc:g}; worst case "
                  f"{_fmt(a['max_loss'])}/sh — real, defined risk.")
        else:  # covered_call
            pctc = cushion / basis * 100 if basis else 0
            print(f"  Downside cushion ≈ {cushion:.2f}/sh ({pctc:.1f}%) — income, "
                  f"NOT real protection; below break-even you eat the full drop.")
    print()


def _premium(direct, iv, days, spot, strike, right):
    """Use the quoted premium if given; else derive it from IV via Black-Scholes."""
    if direct is not None:
        return direct
    if iv is not None and days is not None and strike is not None:
        g = volatility.bs_greeks(spot, strike, days / 365.0, iv / 100.0, right=right)
        return round(g["price"], 2)
    return None


def main():
    ap = argparse.ArgumentParser(description="Option strategy P&L (max profit/loss/break-even)")
    ap.add_argument("--strategy", required=True,
                    choices=["covered_call", "protective_put", "collar",
                             "long_call", "long_put", "short_call"])
    ap.add_argument("--spot", type=float, required=True, help="Current underlying price")
    ap.add_argument("--basis", type=float, help="Share cost basis (default: spot)")
    ap.add_argument("--contracts", type=int, default=1)
    ap.add_argument("--put-strike", type=float)
    ap.add_argument("--put-premium", type=float)
    ap.add_argument("--call-strike", type=float)
    ap.add_argument("--call-premium", type=float)
    ap.add_argument("--iv", type=float, help="Derive missing premiums from this IV %% ...")
    ap.add_argument("--days", type=float, help="... together with days to expiration")
    args = ap.parse_args()

    spot = args.spot
    basis = args.basis if args.basis is not None else spot
    kp, kc = args.put_strike, args.call_strike
    cp = _premium(args.put_premium, args.iv, args.days, spot, kp, "put")
    cc = _premium(args.call_premium, args.iv, args.days, spot, kc, "call")

    need = {
        "covered_call": [("call", kc, cc)],
        "protective_put": [("put", kp, cp)],
        "collar": [("put", kp, cp), ("call", kc, cc)],
        "long_call": [("call", kc, cc)],
        "long_put": [("put", kp, cp)],
        "short_call": [("call", kc, cc)],
    }[args.strategy]
    for label, k, c in need:
        if k is None or c is None:
            ap.error(f"{args.strategy} needs --{label}-strike and --{label}-premium "
                     f"(or --iv and --days to derive the premium).")

    report(args.strategy, spot, basis, kp, cp or 0.0, kc, cc or 0.0, args.contracts)


if __name__ == "__main__":
    main()
