"""
option_position.py — shared option-position helpers (leg model + Greeks).

The pieces both `analyze_position.py` (terminal) and `option_report.py` (Excel)
need: which legs a strategy holds, how to build those legs (from a live/stored
`option_quotes` snapshot or from Black-Scholes offline), and the net position
Greeks. Kept in one place so the two front-ends never duplicate this logic.

Read-only: nothing here writes to the database.
"""

import volatility

# Each strategy's legs as (right, qty_sign). +1 = long/own, -1 = short/sold.
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


def needed_legs(strategy, put_strike, call_strike):
    """[(right, strike), ...] for a strategy, or raise ValueError if a strike is missing."""
    out = []
    for right, _ in STRATEGY_LEGS[strategy]:
        k = put_strike if right == "P" else call_strike
        if k is None:
            side = "put" if right == "P" else "call"
            raise ValueError(f"{strategy} needs a {side} strike")
        out.append((right, k))
    return out


def premium_from_quote(row):
    """Best available premium from a stored quote: mid, else last, else model price."""
    bid, ask = row["bid"], row["ask"]
    if bid is not None and ask is not None:
        return (bid + ask) / 2
    return row["last"] if row["last"] is not None else row["model_price"]


def compute_legs_offline(spot, iv_pct, days, needed):
    """Build legs from Black-Scholes (no DB, no IB). iv_pct is in percent (19.05).

    Returns {(right, strike): {strike, right, iv(decimal), premium, underlying, +Greeks}}."""
    iv = iv_pct / 100.0
    T = days / 365.0
    legs = {}
    for right, k in needed:
        kind = "call" if right == "C" else "put"
        g = volatility.bs_greeks(spot, k, T, iv, right=kind)
        legs[(right, k)] = {"strike": k, "right": right, "iv": iv,
                            "premium": round(g["price"], 2), "underlying": spot, **g}
    return legs


def legs_from_db(db, store, company, expiry, needed):
    """Build legs from the latest stored option_quotes snapshot. Returns (legs, spot)."""
    legs = {}
    quotes = store.get_option_quotes(db, company, expiry=expiry)
    by_key = {(round(q["strike"], 4), q["opt_right"]): q for q in quotes}
    for right, k in needed:
        q = by_key.get((round(k, 4), right))
        if q is None:
            continue
        legs[(right, k)] = {
            "strike": k, "right": right, "iv": q["implied_vol"],
            "premium": premium_from_quote(q), "underlying": q["underlying_price"],
            **{g: q[g] for g in GREEKS},
        }
    spot = next((leg["underlying"] for leg in legs.values() if leg.get("underlying")), None)
    return legs, spot


def position_greeks(strategy, legs, contracts):
    """Net Greeks of the WHOLE position (long shares + option legs), ×100×contracts."""
    mult = 100 * contracts
    net = {g: 0.0 for g in GREEKS}
    if strategy in HAS_STOCK:
        net["delta"] += mult                 # 100 long shares = delta 1.0/sh each
    signs = dict(STRATEGY_LEGS[strategy])
    for (right, _k), leg in legs.items():
        sign = signs.get(right, 0)
        for g in GREEKS:
            v = leg.get(g)
            if v is not None:
                net[g] += sign * v * mult
    return net
