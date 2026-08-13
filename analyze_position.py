#!/usr/bin/env python3
"""
analyze_position.py — one-shot "analyze this option position".

Ties the three engines together into a single command:
  1. LIVE: pull the option chain for the position's legs from IB Gateway and
     store a timestamped snapshot in `option_quotes` (via scrape_ibkr_options).
  2. Print each leg's implied vol + Greeks, then the NET position Greeks
     (delta/gamma/vega/theta/rho of the whole thing, shares included).
  3. Print IV Rank/Percentile (from the accumulated option_quotes history).
  4. Print the strategy P&L — max profit / max loss / break-even + payoff table
     (via option_strategy) using the live premiums just pulled.

Strategies: covered_call, protective_put, collar, long_call, long_put, short_call.

LIVE mode needs IB Gateway on localhost (run it on your machine, not in a cloud
session). --offline skips IB and computes everything from --spot + --iv + --days
with Black-Scholes (still records a snapshot as source='manual' so IV history grows).

Usage:
    # Live (IB Gateway running locally):
    python analyze_position.py --strategy collar --company QQQ --expiry 2026-08-20 \
        --put-strike 713 --call-strike 754 --basis 700

    # Offline (no Gateway) — quote the IV yourself:
    python analyze_position.py --strategy collar --company QQQ --expiry 2026-08-20 \
        --put-strike 713 --call-strike 754 --spot 733.94 --iv 19.05 --days 7 --offline
"""

import argparse
import sys

import store
import volatility
import option_strategy

# Which legs each strategy holds: (right, qty_sign). +1 = long (own), -1 = short (sold).
STRATEGY_LEGS = {
    "covered_call":   [("C", -1)],
    "protective_put": [("P", +1)],
    "collar":         [("P", +1), ("C", -1)],
    "long_call":      [("C", +1)],
    "long_put":       [("P", +1)],
    "short_call":     [("C", -1)],
}
HAS_STOCK = {"covered_call", "protective_put", "collar"}
GREEKS = ("delta", "gamma", "vega", "theta", "rho")


def _premium_from_quote(row):
    """Best available premium from a stored quote: mid, else last, else model."""
    bid, ask = row["bid"], row["ask"]
    if bid is not None and ask is not None:
        return (bid + ask) / 2
    return row["last"] if row["last"] is not None else row["model_price"]


def gather_live(db, args, iso_expiry, needed):
    """Pull the needed strikes from IBKR, store a snapshot, read the legs back."""
    try:
        import scrape_ibkr_options as sio
    except SystemExit:
        raise
    strikes = sorted({k for _, k in needed})
    ib = sio.connect_ibkr(delayed=args.delayed)
    try:
        sio.scrape_options(ib, db, args.company, iso_expiry,
                           strikes=strikes, rights="CP", source="IBKR")
    finally:
        ib.disconnect()

    legs = {}
    quotes = store.get_option_quotes(db, args.company, expiry=iso_expiry)
    by_key = {(round(q["strike"], 4), q["opt_right"]): q for q in quotes}
    for right, k in needed:
        q = by_key.get((round(k, 4), right))
        if q is None:
            print(f"  ! no live quote for {k:g}{right}")
            continue
        legs[(right, k)] = {
            "strike": k, "right": right, "iv": q["implied_vol"],
            "premium": _premium_from_quote(q),
            "underlying": q["underlying_price"],
            **{g: q[g] for g in GREEKS},
        }
    spot = next((leg["underlying"] for leg in legs.values() if leg.get("underlying")), None)
    return legs, spot


def gather_offline(db, args, iso_expiry, needed):
    """Compute each leg's Greeks from --spot/--iv/--days; record a manual snapshot."""
    if args.spot is None or args.iv is None or args.days is None:
        raise SystemExit("--offline needs --spot, --iv and --days.")
    spot, iv, days = args.spot, args.iv / 100.0, args.days
    T = days / 365.0
    snap = store._now()
    legs = {}
    for right, k in needed:
        kind = "call" if right == "C" else "put"
        g = volatility.bs_greeks(spot, k, T, iv, right=kind)
        legs[(right, k)] = {"strike": k, "right": right, "iv": iv,
                            "premium": round(g["price"], 2), "underlying": spot, **g}
        store.add_option_quote(db, args.company, iso_expiry, k, right,
                               underlying_price=spot, implied_vol=iv,
                               delta=g["delta"], gamma=g["gamma"], vega=g["vega"],
                               theta=g["theta"], rho=g["rho"], model_price=g["price"],
                               source="manual", snapshot_at=snap)
    return legs, spot


def position_greeks(strategy, legs, contracts):
    """Net Greeks of the WHOLE position (shares + option legs), ×100×contracts."""
    mult = 100 * contracts
    net = {g: 0.0 for g in GREEKS}
    if strategy in HAS_STOCK:
        net["delta"] += mult                 # 100 long shares = delta 1.0/sh each
    for (right, k), leg in legs.items():
        sign = dict(STRATEGY_LEGS[strategy]).get(right, 0)
        for g in GREEKS:
            v = leg.get(g)
            if v is not None:
                net[g] += sign * v * mult
    return net


def main():
    ap = argparse.ArgumentParser(description="Analyze an option position (Greeks + IV Rank + P&L)")
    ap.add_argument("--db", default=store.DB_PATH)
    ap.add_argument("--strategy", required=True, choices=list(STRATEGY_LEGS))
    ap.add_argument("--company", required=True, help="Underlying name/ticker (e.g. QQQ)")
    ap.add_argument("--expiry", required=True, help="Expiration YYYY-MM-DD or YYYYMMDD")
    ap.add_argument("--put-strike", type=float)
    ap.add_argument("--call-strike", type=float)
    ap.add_argument("--basis", type=float, help="Share cost basis (default: spot)")
    ap.add_argument("--contracts", type=int, default=1)
    ap.add_argument("--lookback", type=int, default=252, help="IV Rank lookback days")
    ap.add_argument("--offline", action="store_true", help="No IB; use --spot/--iv/--days")
    ap.add_argument("--delayed", action="store_true", help="Live mode: use delayed data")
    ap.add_argument("--spot", type=float, help="Offline: underlying price")
    ap.add_argument("--iv", type=float, help="Offline: implied vol in %% (e.g. 19.05)")
    ap.add_argument("--days", type=float, help="Offline: days to expiration")
    args = ap.parse_args()

    iso_expiry = f"{args.expiry[:4]}-{args.expiry[4:6]}-{args.expiry[6:]}" \
        if "-" not in args.expiry else args.expiry

    # Which legs (right, strike) does this strategy need?
    needed = []
    for right, _ in STRATEGY_LEGS[args.strategy]:
        k = args.put_strike if right == "P" else args.call_strike
        if k is None:
            ap.error(f"{args.strategy} needs --{'put' if right == 'P' else 'call'}-strike")
        needed.append((right, k))

    db = store.get_db(args.db)
    store.init_db(db)

    legs, spot = (gather_offline if args.offline else gather_live)(db, args, iso_expiry, needed)
    if not legs or spot is None:
        print("Could not assemble the position (no quotes / no spot).")
        sys.exit(1)
    basis = args.basis if args.basis is not None else spot

    # ---- header ----
    print("\n" + "=" * 56)
    print(f"POSITION: {args.strategy.replace('_', ' ').title()}  ·  "
          f"{args.company} {iso_expiry}  ·  {args.contracts} contract(s)")
    print(f"spot {spot:g}   basis {basis:g}"
          + ("   [offline / model]" if args.offline else "   [live IBKR]"))
    print("=" * 56)

    # ---- per-leg Greeks ----
    print("\nLegs (per share):")
    print(f"  {'leg':>10}  {'IV':>6}  {'prem':>7}  {'delta':>7}  {'gamma':>7}"
          f"  {'vega':>6}  {'theta':>7}  {'rho':>6}")
    for right, k in needed:
        leg = legs.get((right, k))
        if not leg:
            continue
        side = "SELL" if dict(STRATEGY_LEGS[args.strategy])[right] < 0 else "BUY "
        ivp = f"{leg['iv']*100:5.1f}%" if leg["iv"] else "  n/a"
        print(f"  {side} {k:>4g}{right}  {ivp}  {leg['premium']:7.2f}  "
              f"{leg['delta']:+7.3f}  {leg['gamma']:7.4f}  {leg['vega']:6.3f}  "
              f"{leg['theta']:+7.3f}  {leg['rho']:+6.3f}")

    # ---- net position Greeks ----
    net = position_greeks(args.strategy, legs, args.contracts)
    print(f"\nNet position Greeks (×{100*args.contracts} sh):")
    print(f"  delta {net['delta']:+.1f}   gamma {net['gamma']:+.2f}   "
          f"vega {net['vega']:+.1f}/IVpt   theta {net['theta']:+.1f}/day   "
          f"rho {net['rho']:+.1f}/1%")
    print(f"  → ~{'long' if net['delta']>=0 else 'short'} {abs(net['delta']):.0f} "
          f"deltas (moves like {abs(net['delta']):.0f} shares); "
          f"theta {'earns' if net['theta']>=0 else 'costs'} "
          f"~${abs(net['theta']):.0f}/day; "
          f"vega {'gains' if net['vega']>=0 else 'loses'} "
          f"~${abs(net['vega']):.0f} per +1 IV pt.")

    # ---- IV Rank ----
    volatility.iv_rank_report(db, args.company, expiry=iso_expiry, lookback_days=args.lookback)

    # ---- strategy P&L ----
    kp = args.put_strike
    kc = args.call_strike
    cp = legs.get(("P", kp), {}).get("premium", 0.0) if kp is not None else 0.0
    cc = legs.get(("C", kc), {}).get("premium", 0.0) if kc is not None else 0.0
    option_strategy.report(args.strategy, spot, basis, kp, cp or 0.0, kc, cc or 0.0,
                           args.contracts)


if __name__ == "__main__":
    main()
