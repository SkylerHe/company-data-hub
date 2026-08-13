#!/usr/bin/env python3
"""
sheets_export.py — push an option position straight into a Google Sheet.

Same math as option_report.py (Greeks, IV, strategy P&L), but instead of a local
.xlsx it writes the Position / Greeks / Payoff tabs into a Google Sheet via gspread
— the free, Mac-friendly path when Excel isn't licensed. You then insert a chart
from the Payoff tab (Insert ▸ Chart; Sheets suggests a line chart).

One-time setup (all free):
  1. Google Cloud console → enable the **Google Sheets API** (and Drive API).
  2. Create a **service account**, download its JSON key.
  3. Share your target Sheet with the service account's email (Editor).
  4. pip install gspread google-auth   (already in requirements.txt)
  5. point --creds at the JSON, and --sheet-url / --sheet-id at your Sheet.

    python sheets_export.py --strategy collar --company QQQ --expiry 2026-08-20 \
        --put-strike 713 --call-strike 754 --spot 733.94 --iv 19.05 --days 7 \
        --sheet-url 'https://docs.google.com/spreadsheets/d/XXXX/edit' \
        --creds ~/keys/sheets-service-account.json

`build_sheets_data(ctx)` returns the plain 2-D rows per tab; the gspread push is a
thin wrapper, so the data layer is testable without any Google credentials.
"""

import argparse
import os
import sys

import store
import option_strategy
import option_position as op

PAYOFF_SPAN = 0.30
PAYOFF_STEPS = 61


def _net_cash(strategy, legs):
    signs = dict(op.STRATEGY_LEGS[strategy])
    return sum(-signs.get(r, 0) * leg["premium"] for (r, _k), leg in legs.items())


def _money(v):
    inf = float("inf")
    return "unlimited" if v == inf else ("-unlimited" if v == -inf else round(v, 2))


def build_sheets_data(ctx):
    """Return {tab_name: [[row], ...]} — the exact grid written to each worksheet."""
    a = option_strategy.analyze(ctx["strategy"], ctx["spot"], ctx["basis"],
                                ctx["kp"], ctx["cp"], ctx["kc"], ctx["cc"], ctx["contracts"])
    net = op.position_greeks(ctx["strategy"], ctx["legs"], ctx["contracts"])
    mult = a["mult"]
    title = ctx["strategy"].replace("_", " ").title()

    position = [
        [f"{title} — {ctx['company']} {ctx['expiry']}"],
        [f"Source: {ctx['source']} (Python-computed)"],
        [],
        ["INPUTS", ""],
        ["Underlying spot", round(ctx["spot"], 2)],
        ["Share cost basis", round(ctx["basis"], 2)],
        ["Contracts (x100 sh)", ctx["contracts"]],
        ["Net premium (+credit/-debit)", round(_net_cash(ctx["strategy"], ctx["legs"]), 2)],
        [],
        ["P&L", "per share", "total"],
        ["Max profit", _money(a["max_profit"]),
         _money(a["max_profit"] * mult) if abs(a["max_profit"]) != float("inf") else _money(a["max_profit"])],
        ["Max loss", _money(a["max_loss"]),
         _money(a["max_loss"] * mult) if abs(a["max_loss"]) != float("inf") else _money(a["max_loss"])],
        ["Break-even(s)", ", ".join(f"{b:g}" for b in a["break_evens"]) or "-"],
        [],
        [f"NET POSITION GREEKS (x{mult} sh)", ""],
        ["delta (per $1)", round(net["delta"], 3)],
        ["gamma (per $1^2)", round(net["gamma"], 3)],
        ["vega (per +1 IV pt)", round(net["vega"], 3)],
        ["theta (per day)", round(net["theta"], 3)],
        ["rho (per +1% rate)", round(net["rho"], 3)],
    ]

    greeks = [["Leg", "Side", "Strike", "IV", "Premium",
               "Delta", "Gamma", "Vega", "Theta", "Rho"]]
    signs = dict(op.STRATEGY_LEGS[ctx["strategy"]])
    for right, k in ctx["needed"]:
        leg = ctx["legs"].get((right, k))
        if not leg:
            continue
        greeks.append([
            f"{k:g}{right}", "SELL" if signs.get(right, 0) < 0 else "BUY", k,
            round(leg["iv"], 4) if leg.get("iv") is not None else None,
            round(leg["premium"], 2),
            *[round(leg[g], 5) if leg.get(g) is not None else None for g in op.GREEKS],
        ])
    greeks.append(["NET", "", "", "", "", *[round(net[g], 3) for g in op.GREEKS]])

    payoff = [["Underlying", "P&L / share", "P&L total"]]
    lo, hi = ctx["spot"] * (1 - PAYOFF_SPAN), ctx["spot"] * (1 + PAYOFF_SPAN)
    step = (hi - lo) / (PAYOFF_STEPS - 1)
    for i in range(PAYOFF_STEPS):
        S = lo + i * step
        y = option_strategy._payoff(ctx["strategy"], S, ctx["spot"], ctx["basis"],
                                    ctx["kp"], ctx["cp"], ctx["kc"], ctx["cc"])
        payoff.append([round(S, 2), round(y, 2), round(y * mult, 2)])

    return {"Position": position, "Greeks": greeks, "Payoff": payoff}


def push_to_sheets(data, *, sheet_id=None, sheet_url=None, creds_path=None):
    """Write each tab of `data` into the target Google Sheet (thin gspread wrapper)."""
    import gspread
    gc = gspread.service_account(filename=creds_path) if creds_path else gspread.service_account()
    if sheet_url:
        ss = gc.open_by_url(sheet_url)
    elif sheet_id:
        ss = gc.open_by_key(sheet_id)
    else:
        raise ValueError("need --sheet-url or --sheet-id")

    existing = {ws.title: ws for ws in ss.worksheets()}
    for tab, rows in data.items():
        ncols = max((len(r) for r in rows), default=1)
        if tab in existing:
            ws = existing[tab]
            ws.clear()
        else:
            ws = ss.add_worksheet(title=tab, rows=len(rows) + 5, cols=ncols + 2)
        ws.update(rows, value_input_option="USER_ENTERED")
    return ss.url


def main():
    ap = argparse.ArgumentParser(description="Push an option position into a Google Sheet")
    ap.add_argument("--db", default=store.DB_PATH)
    ap.add_argument("--strategy", required=True, choices=list(op.STRATEGY_LEGS))
    ap.add_argument("--company", required=True)
    ap.add_argument("--expiry", required=True, help="YYYY-MM-DD or YYYYMMDD")
    ap.add_argument("--put-strike", type=float)
    ap.add_argument("--call-strike", type=float)
    ap.add_argument("--basis", type=float)
    ap.add_argument("--contracts", type=int, default=1)
    ap.add_argument("--spot", type=float, help="Offline: underlying price")
    ap.add_argument("--iv", type=float, help="Offline: implied vol %% (e.g. 19.05)")
    ap.add_argument("--days", type=float, help="Offline: days to expiration")
    ap.add_argument("--sheet-url", help="Target Google Sheet URL")
    ap.add_argument("--sheet-id", help="Target Google Sheet key/id")
    ap.add_argument("--creds", help="Service-account JSON path "
                                    "(else GOOGLE_APPLICATION_CREDENTIALS / gspread default)")
    ap.add_argument("--dry-run", action="store_true", help="Print the tabs; don't call Google")
    args = ap.parse_args()

    offline = args.spot is not None and args.iv is not None and args.days is not None
    db = None if offline else store.get_db(args.db)
    try:
        ctx = op.build_context(db, args.strategy, args.company, args.expiry,
                               args.put_strike, args.call_strike, basis=args.basis,
                               contracts=args.contracts, spot=args.spot,
                               iv=args.iv, days=args.days)
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    data = build_sheets_data(ctx)
    if args.dry_run:
        for tab, rows in data.items():
            print(f"\n== {tab} ({len(rows)} rows) ==")
            for r in rows[:8]:
                print("  ", r)
        return

    url = push_to_sheets(data, sheet_id=args.sheet_id, sheet_url=args.sheet_url,
                         creds_path=args.creds or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
    print(f"Wrote Position / Greeks / Payoff to {url}")
    print("In Sheets: open the Payoff tab → Insert ▸ Chart for the payoff diagram.")


if __name__ == "__main__":
    main()
