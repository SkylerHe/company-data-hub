"""
option_position.py — shared option-position helpers (leg model + Greeks).

The pieces both `analyze_position.py` (terminal) and `option_report.py` (Excel)
need: which legs a strategy holds, how to build those legs (from a live/stored
`option_quotes` snapshot or from Black-Scholes offline), and the net position
Greeks. Kept in one place so the two front-ends never duplicate this logic.

Read-only: nothing here writes to the database.
"""

import store
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


def iso_expiry(s):
    """Normalize 'YYYYMMDD' or 'YYYY-MM-DD' to 'YYYY-MM-DD'."""
    return s if "-" in s else f"{s[:4]}-{s[4:6]}-{s[6:]}"


def legs_from_db(db, company, expiry, needed):
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


def add_position_args(ap):
    """Register the CLI args common to the option exporters (option_report, sheets_export)."""
    ap.add_argument("--db", default=store.DB_PATH)
    ap.add_argument("--strategy", required=True, choices=list(STRATEGY_LEGS))
    ap.add_argument("--company", required=True)
    ap.add_argument("--expiry", required=True, help="YYYY-MM-DD or YYYYMMDD")
    ap.add_argument("--put-strike", type=float)
    ap.add_argument("--call-strike", type=float)
    ap.add_argument("--basis", type=float, help="Share cost basis (default: spot)")
    ap.add_argument("--contracts", type=int, default=1)
    ap.add_argument("--spot", type=float, help="Offline: underlying price")
    ap.add_argument("--iv", type=float, help="Offline: implied vol %% (e.g. 19.05)")
    ap.add_argument("--days", type=float, help="Offline: days to expiration")


def context_from_args(args):
    """Build the position context from parsed args (offline if spot/iv/days, else DB)."""
    offline = args.spot is not None and args.iv is not None and args.days is not None
    db = None if offline else store.get_db(args.db)
    return build_context(db, args.strategy, args.company, args.expiry,
                         args.put_strike, args.call_strike, basis=args.basis,
                         contracts=args.contracts, spot=args.spot, iv=args.iv, days=args.days)


def build_context(db, strategy, company, expiry, put_strike, call_strike,
                  basis=None, contracts=1, spot=None, iv=None, days=None):
    """Assemble the position dict both exporters (Excel, Sheets) render from.

    Offline when spot+iv+days are all given (Black-Scholes); otherwise reads the
    latest stored option_quotes snapshot from `db`. Raises ValueError on bad/missing
    inputs (no strike, no data)."""
    exp = iso_expiry(expiry)
    needed = needed_legs(strategy, put_strike, call_strike)
    if spot is not None and iv is not None and days is not None:
        legs, spot_out, source = compute_legs_offline(spot, iv, days, needed), spot, \
            "offline / Black-Scholes"
    else:
        if db is None:
            raise ValueError("need --spot/--iv/--days or a db with stored quotes")
        legs, spot_out = legs_from_db(db, company, exp, needed)
        source = "stored option_quotes snapshot"
        if not legs or spot_out is None:
            raise ValueError(f"no stored quotes for {company} {exp}; scrape first "
                             "or pass --spot/--iv/--days")
    return {
        "strategy": strategy, "company": company, "expiry": exp,
        "legs": legs, "needed": needed, "spot": spot_out,
        "basis": basis if basis is not None else spot_out,
        "contracts": contracts, "source": source,
        "kp": put_strike, "kc": call_strike,
        "cp": legs.get(("P", put_strike), {}).get("premium", 0.0) or 0.0,
        "cc": legs.get(("C", call_strike), {}).get("premium", 0.0) or 0.0,
    }
