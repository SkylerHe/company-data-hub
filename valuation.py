#!/usr/bin/env python3
"""
valuation.py — intrinsic-value engine (read-only over finance.db).

Where analyze.py answers "is this a good business?", this answers "what is it
worth, and is today's price a bargain?" It builds on analyze.py's data access
(same EDGAR series + Yahoo snapshot) and adds the valuation machinery a value
investor actually runs:

  - CAPM cost of equity  (rf + beta·ERP)
  - WACC                 (equity/debt-weighted, after-tax cost of debt)
  - 2-stage FCFF DCF     (stage-1 growth for N years → Gordon terminal value)
  - Reverse DCF          (what FCF growth is today's price implying?)
  - Peer-median comps    (multiples from same-industry names in THIS db)
  - Bear / base / bull scenarios
  - Margin-of-safety verdict against the current price

Design stance — honest about assumptions:
  A DCF is only as good as its inputs, and several inputs are *assumptions*, not
  facts in the db (risk-free rate, equity risk premium, cost of debt, terminal
  growth). Every one has a documented default AND a CLI override, and the output
  labels them as assumptions. The engine COMPUTES; it never claims a single
  number is "the" value — it produces a range and a margin of safety, and the
  value-company skill interprets. This matches the repo's evidence-based rule:
  nothing is asserted that can't be traced to a stored number or a stated
  assumption.

  The stored `free_cash_flow` is OCF − capex (post-interest), so discounting it
  at WACC to an enterprise value is a common, teachable simplification rather
  than a textbook-pure FCFF. The report says so; don't over-trust the last digit.

Pure stdlib. No writes.

    python valuation.py --company MSFT
    python valuation.py --company MSFT --json
    python valuation.py --company MSFT --growth 0.10 --rf 0.045 --erp 0.05
    python valuation.py --company MSFT --mos 0.30      # require 30% margin of safety
"""

import argparse
import json
import sys
from statistics import median

import analyze
import store

# ----------------------------------------------------------------------------
# Default assumptions — all overridable on the CLI. These are the inputs a DCF
# is most sensitive to, so they live in one place and are echoed in every report
# so the user can see (and challenge) exactly what drove the number.
# ----------------------------------------------------------------------------
DEFAULTS = {
    "rf":              0.043,  # risk-free rate — US 10Y Treasury area, mid-2026.
                               #   ASSUMPTION: update from the live Treasury yield.
    "erp":             0.050,  # equity risk premium — long-run (Damodaran-style).
    "cost_of_debt":    0.055,  # pre-tax cost of debt — ASSUMPTION (EDGAR's
                               #   standardized set has no interest expense).
    "tax_rate":        0.21,   # US statutory corporate rate.
    "terminal_growth": 0.025,  # perpetual growth ~ long-run nominal GDP.
    "forecast_years":  5,      # stage-1 horizon.
    "mos_required":    0.25,   # margin of safety demanded before "BUY".
    "beta_fallback":   1.0,    # if Yahoo has no beta.
}

# Bounds keep an extrapolated historical CAGR from producing an absurd forecast.
G1_MIN, G1_MAX = 0.02, 0.15


# ----------------------------------------------------------------------------
# Data access (thin wrappers over analyze.py + store)
# ----------------------------------------------------------------------------
def _latest(s: dict):
    """Most recent value of a period-keyed EDGAR series ('FY####')."""
    return s[sorted(s)[-1]] if s else None


def current_price(db, company: str):
    """Latest stored close for the company."""
    rows = store.get_prices(db, company, field="close")
    return rows[-1][1] if rows else None


def peer_multiples(db, company: str):
    """Median current multiple across same-industry names in this db.

    Genuinely evidence-based comps: peers come from the user's own tracked
    universe via the industry linkage, not a hard-coded market average. Returns
    {multiple: (median, n_peers)} only for multiples with >= 3 peer data points,
    so a thin peer set degrades to "not enough peers" rather than a noisy guess.
    """
    peers = set()
    for ind in store.industries_of(db, company):
        peers.update(store.companies_in_industry(db, ind))
    peers.discard(company)

    out = {}
    for m in ("pe_ratio", "ps_ratio", "ev_ebitda"):
        vals = []
        for p in peers:
            v = analyze.snapshot(db, p, m)
            # Multiples must be positive to be meaningful (negative P/E = losses).
            if isinstance(v, (int, float)) and v > 0:
                vals.append(v)
        if len(vals) >= 3:
            out[m] = (median(vals), len(vals))
    return out, len(peers)


# ----------------------------------------------------------------------------
# Cost of capital
# ----------------------------------------------------------------------------
def cost_of_equity(rf, beta, erp):
    """CAPM: the return equity holders demand for this stock's market risk."""
    return rf + beta * erp


def wacc(ke, kd, tax, equity_value, debt_value):
    """Blended discount rate, weighted by market value of equity vs debt.
    Falls back to pure cost of equity when there's no debt (or no weights)."""
    e, d = equity_value or 0, debt_value or 0
    if e + d <= 0:
        return ke
    return (e / (e + d)) * ke + (d / (e + d)) * kd * (1 - tax)


# ----------------------------------------------------------------------------
# DCF
# ----------------------------------------------------------------------------
def dcf_enterprise_value(fcf0, g1, years, disc, g_term):
    """2-stage FCFF DCF → enterprise value.

    Stage 1: fcf0 grows at g1 for `years`, each year discounted at `disc`.
    Stage 2: a Gordon-growth perpetuity at g_term on the final-year FCF.
    Returns None when the model degenerates (disc <= g_term makes the terminal
    value blow up / go negative — a signal the assumptions are inconsistent).
    """
    if fcf0 is None or fcf0 <= 0 or disc <= g_term:
        return None
    pv, fcf = 0.0, fcf0
    for t in range(1, years + 1):
        fcf *= (1 + g1)
        pv += fcf / (1 + disc) ** t
    terminal = fcf * (1 + g_term) / (disc - g_term)
    pv += terminal / (1 + disc) ** years
    return pv


def equity_per_share(ev, net_debt, shares):
    """Enterprise value → equity value → per-share intrinsic value."""
    if ev is None or not shares:
        return None
    return (ev - (net_debt or 0)) / shares


def reverse_dcf_growth(target_equity, fcf0, years, disc, g_term, net_debt):
    """Solve for the stage-1 growth the *current price* implies (bisection).

    Answers "what future does the market already believe?" — the cleanest reality
    check on a DCF. If the implied growth dwarfs the company's history, the price
    is baking in optimism; if it's below history, pessimism.
    """
    if fcf0 is None or fcf0 <= 0 or target_equity is None:
        return None
    target_ev = target_equity + (net_debt or 0)

    def ev_at(g):
        return dcf_enterprise_value(fcf0, g, years, disc, g_term)

    lo, hi = -0.50, 1.0
    ev_lo, ev_hi = ev_at(lo), ev_at(hi)
    if ev_lo is None or ev_hi is None:
        return None
    if not (ev_lo <= target_ev <= ev_hi):
        return None  # price is outside what any plausible growth explains
    for _ in range(100):
        mid = (lo + hi) / 2
        ev_mid = ev_at(mid)
        if ev_mid is None:
            return None
        if ev_mid < target_ev:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ----------------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------------
def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def value_company(db, company: str, overrides: dict | None = None) -> dict:
    """Assemble the full valuation picture for one company."""
    a = {**DEFAULTS, **(overrides or {})}
    g = lambda m: analyze.series(db, company, m)  # noqa: E731

    fcf      = g("free_cash_flow")
    revenue  = g("revenue")
    net_inc  = g("net_income")
    op_inc   = g("operating_income")
    edgar_sh = g("shares_diluted")

    # --- Inputs -----------------------------------------------------------
    price     = current_price(db, company)
    beta      = analyze.snapshot(db, company, "beta") or a["beta_fallback"]
    mkt_cap   = analyze.snapshot(db, company, "market_cap")
    total_debt = analyze.snapshot(db, company, "total_debt") or 0.0
    cash      = analyze.snapshot(db, company, "cash") or 0.0
    # Current shares from Yahoo (more timely than EDGAR); fall back to filings.
    shares    = analyze.snapshot(db, company, "shares_outstanding") or _latest(edgar_sh)
    net_debt  = total_debt - cash

    fcf0      = _latest(fcf)
    fcf_avg3  = None
    if fcf:
        recent = [fcf[p] for p in sorted(fcf)[-3:]]
        fcf_avg3 = sum(recent) / len(recent)

    # Equity value used for weighting WACC: prefer market cap, else price×shares.
    equity_value = mkt_cap or (price * shares if price and shares else None)

    # --- Growth assumption -------------------------------------------------
    # Base stage-1 growth: the company's own historical FCF CAGR, clamped to a
    # sane band; fall back to revenue CAGR, then a conservative default.
    hist_fcf_cagr = analyze._cagr(fcf)
    hist_rev_cagr = analyze._cagr(revenue)
    if overrides and "growth" in overrides:
        g_base = overrides["growth"]
    else:
        raw = hist_fcf_cagr if hist_fcf_cagr is not None else hist_rev_cagr
        g_base = _clamp(raw, G1_MIN, G1_MAX) if raw is not None else 0.08

    # --- Cost of capital ---------------------------------------------------
    ke = cost_of_equity(a["rf"], beta, a["erp"])
    disc = wacc(ke, a["cost_of_debt"], a["tax_rate"], equity_value, total_debt)

    # --- Scenarios ---------------------------------------------------------
    # One lever (stage-1 growth) flexed around the base; discount + terminal held
    # fixed so the driver of the range is transparent.
    spread = 0.04
    scen_growth = {
        "bear": max(a["terminal_growth"], g_base - spread),
        "base": g_base,
        "bull": g_base + spread,
    }
    scenarios = {}
    for name, g1 in scen_growth.items():
        ev = dcf_enterprise_value(fcf0, g1, a["forecast_years"], disc, a["terminal_growth"])
        ivps = equity_per_share(ev, net_debt, shares)
        scenarios[name] = {
            "growth": g1,
            "enterprise_value": ev,
            "intrinsic_per_share": ivps,
        }

    intrinsic = scenarios["base"]["intrinsic_per_share"]

    # --- Reverse DCF -------------------------------------------------------
    implied_g = None
    if price and shares:
        implied_g = reverse_dcf_growth(
            price * shares, fcf0, a["forecast_years"], disc, a["terminal_growth"], net_debt
        )

    # --- Comps -------------------------------------------------------------
    comps = _comps(db, company, revenue, net_inc, op_inc, shares, net_debt)

    # --- Margin of safety & verdict ---------------------------------------
    mos = analyze._div(intrinsic - price, intrinsic) if (intrinsic and price) else None
    verdict = _verdict(price, intrinsic, mos, a["mos_required"])

    return {
        "company": company,
        "price": price,
        "assumptions": {
            "risk_free": a["rf"], "equity_risk_premium": a["erp"], "beta": beta,
            "cost_of_equity": ke, "cost_of_debt": a["cost_of_debt"],
            "tax_rate": a["tax_rate"], "wacc": disc,
            "terminal_growth": a["terminal_growth"],
            "forecast_years": a["forecast_years"],
            "stage1_growth": g_base, "mos_required": a["mos_required"],
        },
        "inputs": {
            "fcf_latest": fcf0, "fcf_avg_3y": fcf_avg3,
            "shares": shares, "market_cap": mkt_cap,
            "total_debt": total_debt, "cash": cash, "net_debt": net_debt,
            "hist_fcf_cagr": hist_fcf_cagr, "hist_revenue_cagr": hist_rev_cagr,
            "fcf_periods": sorted(fcf),
        },
        "dcf": {
            "intrinsic_per_share": intrinsic,
            "enterprise_value": scenarios["base"]["enterprise_value"],
        },
        "scenarios": scenarios,
        "reverse_dcf": {
            "implied_stage1_growth": implied_g,
            "hist_fcf_cagr": hist_fcf_cagr,
        },
        "comps": comps,
        "margin_of_safety": mos,
        "verdict": verdict,
    }


def _comps(db, company, revenue, net_inc, op_inc, shares, net_debt):
    """Peer-median-multiple cross-check. Applies each peer-derived multiple to
    the target's own trailing metric to get an implied per-share value."""
    mult, n_peers = peer_multiples(db, company)
    if not mult or not shares:
        return {"peers": n_peers, "available": bool(mult), "values": {}}

    rev0, ni0, ebit0 = _latest(revenue), _latest(net_inc), _latest(op_inc)
    values = {}
    if "pe_ratio" in mult and ni0:
        med, n = mult["pe_ratio"]
        values["P/E"] = {"multiple": med, "peers": n,
                         "implied_per_share": med * (ni0 / shares)}
    if "ps_ratio" in mult and rev0:
        med, n = mult["ps_ratio"]
        values["P/S"] = {"multiple": med, "peers": n,
                         "implied_per_share": med * (rev0 / shares)}
    if "ev_ebitda" in mult and ebit0:
        # EDGAR's standardized set has no D&A, so EBIT (operating income) proxies
        # EBITDA here — implied value is conservative (understated). Flagged.
        med, n = mult["ev_ebitda"]
        ev = med * ebit0
        values["EV/EBIT(≈EBITDA)"] = {"multiple": med, "peers": n,
                                      "implied_per_share": (ev - net_debt) / shares}
    return {"peers": n_peers, "available": True, "values": values}


def _verdict(price, intrinsic, mos, mos_req):
    """Margin-of-safety decision — value-investing discipline, not a price target."""
    if not price or not intrinsic:
        return {"call": "N/A", "reason": "insufficient data for a DCF "
                "(need positive FCF, shares, and a current price)"}
    if mos >= mos_req:
        return {"call": "BUY", "reason": f"trades {mos*100:.0f}% below base-case "
                f"intrinsic value — clears the {mos_req*100:.0f}% margin-of-safety bar"}
    if mos >= 0:
        return {"call": "HOLD / WATCH", "reason": f"only {mos*100:.0f}% below "
                f"intrinsic — inside the estimate's error bars, no margin of safety"}
    return {"call": "AVOID / OVERVALUED", "reason": f"trades {-mos*100:.0f}% ABOVE "
            f"base-case intrinsic value"}


# ----------------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------------
def _money(x):
    """Human $ with scale suffix."""
    if not isinstance(x, (int, float)):
        return "   -   "
    a = abs(x)
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if a >= div:
            return f"${x/div:,.2f}{suf}"
    return f"${x:,.2f}"


def _pct(x):
    return f"{x*100:.1f}%" if isinstance(x, (int, float)) else "  -  "


def _ps(x):
    return f"${x:,.2f}" if isinstance(x, (int, float)) else "  -  "


def format_report(d: dict) -> str:
    if not d["dcf"]["intrinsic_per_share"] and not d["comps"]["values"]:
        return (f"Can't value {d['company']} — need a positive FCF history "
                f"(run scrape_edgar_financials.py) and a current price/shares.\n"
                f"  fcf_latest={d['inputs']['fcf_latest']} shares={d['inputs']['shares']} "
                f"price={d['price']}")

    a, inp = d["assumptions"], d["inputs"]
    L = [f"Valuation — {d['company']}", "=" * 60]
    L.append(f"Current price: {_ps(d['price'])}    "
             f"Market cap: {_money(inp['market_cap'])}    "
             f"FCF (latest FY): {_money(inp['fcf_latest'])}")
    if inp["fcf_periods"]:
        L.append(f"FCF history: {', '.join(inp['fcf_periods'])}   "
                 f"(hist FCF CAGR {_pct(inp['hist_fcf_cagr'])})")

    L.append("\nAssumptions (all overridable — challenge these):")
    L.append(f"  risk-free {_pct(a['risk_free'])}  +  beta {a['beta']:.2f} × ERP "
             f"{_pct(a['equity_risk_premium'])}  =>  cost of equity {_pct(a['cost_of_equity'])}")
    L.append(f"  WACC {_pct(a['wacc'])}   (cost of debt {_pct(a['cost_of_debt'])} "
             f"after {_pct(a['tax_rate'])} tax)")
    L.append(f"  stage-1 growth {_pct(a['stage1_growth'])} for {a['forecast_years']}y  ->  "
             f"terminal {_pct(a['terminal_growth'])}")

    L.append("\n2-stage DCF — scenarios (lever = stage-1 FCF growth):")
    L.append(f"  {'':<8}{'growth':>9}{'intrinsic/sh':>16}{'up/downside':>13}")
    for name in ("bear", "base", "bull"):
        s = d["scenarios"][name]
        ivps = s["intrinsic_per_share"]
        # Upside = how far price must move to reach intrinsic, i.e. the return
        # you'd earn if the DCF is right: (intrinsic − price) / price.
        gap = analyze._div(ivps - d["price"], d["price"]) if (ivps and d["price"]) else None
        tag = " ◄ base" if name == "base" else ""
        L.append(f"  {name:<8}{_pct(s['growth']):>9}{_ps(ivps):>16}{_pct(gap):>13}{tag}")

    rv = d["reverse_dcf"]["implied_stage1_growth"]
    L.append("\nReverse DCF (what the price already assumes):")
    if rv is not None:
        L.append(f"  market is pricing in ~{_pct(rv)} FCF growth vs "
                 f"{_pct(d['reverse_dcf']['hist_fcf_cagr'])} historical")
        if d["reverse_dcf"]["hist_fcf_cagr"] is not None:
            L.append("    → " + ("price bakes in growth ABOVE history — optimistic"
                     if rv > d["reverse_dcf"]["hist_fcf_cagr"] else
                     "price assumes growth BELOW history — conservative"))
    else:
        L.append("  price sits outside the range any plausible growth explains "
                 "(model can't back out an implied rate)")

    c = d["comps"]
    L.append(f"\nComps cross-check (peer medians from {c['peers']} same-industry names):")
    if c["values"]:
        for k, v in c["values"].items():
            L.append(f"  {k:<18} {v['multiple']:.1f}× ({v['peers']} peers)  ->  "
                     f"{_ps(v['implied_per_share'])}/sh")
    else:
        L.append("  not enough peers with clean multiples in the db (need ≥3) — "
                 "DCF stands alone here")

    L.append("\n" + "-" * 60)
    L.append(f"Margin of safety: {_pct(d['margin_of_safety'])}  "
             f"(discount to base intrinsic; require ≥ {_pct(a['mos_required'])} to BUY)")
    v = d["verdict"]
    L.append(f"VERDICT: {v['call']} — {v['reason']}")
    L.append("\nA model, not a fact: outputs move with the assumptions above. "
             "Treat the scenario range, not a single number, as the answer.")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Intrinsic-value engine (read-only)")
    ap.add_argument("--db", default=store.DB_PATH)
    ap.add_argument("--company", required=True, help="company name or ticker")
    ap.add_argument("--json", action="store_true", help="emit raw JSON")
    # Assumption overrides
    ap.add_argument("--growth", type=float, help="stage-1 FCF growth (e.g. 0.10)")
    ap.add_argument("--rf", type=float, help="risk-free rate")
    ap.add_argument("--erp", type=float, help="equity risk premium")
    ap.add_argument("--cost-of-debt", type=float, dest="cost_of_debt")
    ap.add_argument("--tax", type=float, dest="tax_rate")
    ap.add_argument("--terminal", type=float, dest="terminal_growth")
    ap.add_argument("--years", type=int, dest="forecast_years")
    ap.add_argument("--mos", type=float, dest="mos_required", help="required margin of safety")
    args = ap.parse_args()

    overrides = {k: v for k, v in vars(args).items()
                 if k in DEFAULTS and v is not None}
    if args.growth is not None:
        overrides["growth"] = args.growth

    db = store.get_db(args.db)
    name = analyze.resolve_company(db, args.company)
    if not name:
        print(f"'{args.company}' not found in {args.db}", file=sys.stderr)
        sys.exit(1)

    data = value_company(db, name, overrides)
    print(json.dumps(data, indent=2) if args.json else format_report(data))
    db.close()


if __name__ == "__main__":
    main()
