#!/usr/bin/env python3
"""
industry.py — peer-comparison / relative-valuation engine (read-only over finance.db).

analyze.py reads ONE company's health; valuation.py values ONE company. This is
the third lens: how a company stacks up against its *peers*, and what an entire
industry looks like side by side. It's the data engine behind the `map-industry`
skill and the natural companion to value-company's comps (same peer set, fuller
picture).

For an industry (or a company → each industry it belongs to) it gathers every
member from the db's industry linkage and lays them out across the axes that
actually separate winners from also-rans:
  - size        (market cap, revenue)
  - growth      (revenue CAGR from the EDGAR series)
  - profitability (operating & net margin, ROE)   — from EDGAR statements
  - valuation   (P/E, P/S, EV/EBITDA, P/B)         — from the Yahoo snapshot
Then it computes the industry medians and ranks the field: biggest, most
profitable, fastest-growing, cheapest and richest vs. peers.

Two data sources, same split the rest of the repo uses:
  EDGAR series  → fundamentals (growth, margins, returns) — consistent, multi-year
  Yahoo snapshot → current market multiples EDGAR can't give

Read-only. Pure stdlib (+ the repo's analyze/store).

    python industry.py --industry Semiconductors
    python industry.py --company NVIDIA          # maps every industry NVDA is in
    python industry.py --industry "Cloud & Software" --json
"""

import argparse
import json
import sys
from statistics import median

import analyze
import store


# ----------------------------------------------------------------------------
# Selection
# ----------------------------------------------------------------------------
def resolve_industry(db, query: str):
    """Exact-then-fuzzy match on an industry name."""
    row = db.execute("SELECT name FROM industries WHERE name = ? LIMIT 1",
                     (query,)).fetchone()
    if row:
        return row[0]
    row = db.execute("SELECT name FROM industries WHERE name LIKE ? LIMIT 1",
                     (f"%{query}%",)).fetchone()
    return row[0] if row else None


def targets(db, args):
    """Return [(industry_name, focus_company_or_None), ...] to map.
    --industry maps that one; --company maps every industry it belongs to."""
    if args.industry:
        ind = resolve_industry(db, args.industry)
        if not ind:
            return []
        return [(ind, None)]
    name = analyze.resolve_company(db, args.company)
    if not name:
        return []
    inds = store.industries_of(db, name)
    return [(ind, name) for ind in inds]


def _ticker(db, name: str) -> str:
    r = db.execute("SELECT ticker FROM instruments WHERE name = ?", (name,)).fetchone()
    return r[0] if r and r[0] else "?"


def _stock_members(db, industry: str) -> list[str]:
    """Industry members that are actual operating companies. ETFs/funds get
    tagged to industries too (e.g. SMH under Semiconductors) but have no
    statements or single-company multiples, so they don't belong in a peer
    comparison — filter them out."""
    members = store.companies_in_industry(db, industry)
    out = []
    for m in members:
        r = db.execute("SELECT asset_class FROM instruments WHERE name = ?", (m,)).fetchone()
        if r and r[0] == "stock":
            out.append(m)
    return out


# ----------------------------------------------------------------------------
# Per-company metrics
# ----------------------------------------------------------------------------
def _latest(s: dict):
    return s[sorted(s)[-1]] if s else None


def company_metrics(db, name: str) -> dict:
    """The comparable line for one company: size, growth, profitability, value.
    Fundamentals come from the EDGAR series; multiples from the Yahoo snapshot.
    Any field the data can't support comes back None and is shown as '-'."""
    g = lambda m: analyze.series(db, name, m)  # noqa: E731
    rev, ni, op, eq = g("revenue"), g("net_income"), g("operating_income"), g("total_equity")
    rev0 = _latest(rev)
    snap = lambda m: analyze.snapshot(db, name, m)  # noqa: E731
    return {
        "name": name,
        "ticker": _ticker(db, name),
        "market_cap": snap("market_cap"),
        "revenue": rev0,
        "rev_cagr": analyze._cagr(rev),
        "op_margin": analyze._div(_latest(op), rev0),
        "net_margin": analyze._div(_latest(ni), rev0),
        "roe": analyze._div(_latest(ni), _latest(eq)),
        "pe": snap("pe_ratio"),
        "ps": snap("ps_ratio"),
        "ev_ebitda": snap("ev_ebitda"),
        "pb": snap("pb_ratio"),
    }


# Which metrics we summarize, and whether "cheap/best" means high or low.
_METRICS = ("market_cap", "revenue", "rev_cagr", "op_margin", "net_margin",
            "roe", "pe", "ps", "ev_ebitda", "pb")
# Sizes and multiples are only meaningful when positive; margins/growth/ROE can
# legitimately be negative (a loss-making or shrinking peer), so keep those.
_POSITIVE_ONLY = ("market_cap", "revenue", "pe", "ps", "ev_ebitda", "pb")


def _median(rows, key):
    if key in _POSITIVE_ONLY:
        vals = [r[key] for r in rows if isinstance(r[key], (int, float)) and r[key] > 0]
    else:
        vals = [r[key] for r in rows if isinstance(r[key], (int, float))]
    return median(vals) if vals else None


def _best(rows, key, want="max"):
    """The company row with the highest (or lowest) value of `key`. Multiples
    are only meaningful when positive, so non-positive values are ignored."""
    positive_only = key in ("pe", "ps", "ev_ebitda", "pb")
    cand = [r for r in rows if isinstance(r[key], (int, float))
            and (r[key] > 0 if positive_only else True)]
    if not cand:
        return None
    return (min if want == "min" else max)(cand, key=lambda r: r[key])


def map_industry(db, industry: str, focus: str | None = None) -> dict:
    """Assemble the full comparison for one industry."""
    members = _stock_members(db, industry)
    rows = [company_metrics(db, m) for m in members]
    # Sort by size (market cap) so the table reads leaders-first.
    rows.sort(key=lambda r: r["market_cap"] or 0, reverse=True)

    medians = {k: _median(rows, k) for k in _METRICS}
    leaders = {
        "largest":         _best(rows, "market_cap", "max"),
        "most_profitable": _best(rows, "net_margin", "max"),
        "highest_roe":     _best(rows, "roe", "max"),
        "fastest_growing": _best(rows, "rev_cagr", "max"),
        "cheapest_pe":     _best(rows, "pe", "min"),
        "cheapest_ev":     _best(rows, "ev_ebitda", "min"),
        "richest_pe":      _best(rows, "pe", "max"),
    }
    return {
        "industry": industry,
        "focus": focus,
        "n": len(rows),
        "companies": rows,
        "medians": medians,
        "leaders": leaders,
    }


# ----------------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------------
def _money(x):
    if not isinstance(x, (int, float)):
        return "   -  "
    a = abs(x)
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if a >= div:
            return f"${x/div:.1f}{suf}"
    return f"${x:.0f}"


def _pct(x):
    return f"{x*100:.0f}%" if isinstance(x, (int, float)) else "  -"


def _x(x):
    return f"{x:.1f}" if isinstance(x, (int, float)) and x > 0 else "  -"


def _name(r, focus):
    mark = "►" if r["name"] == focus else " "
    return f"{mark}{r['ticker']:<5}"


def format_report(d: dict) -> str:
    if d["n"] == 0:
        return f"No companies mapped for industry '{d['industry']}'."
    foc = d["focus"]
    L = [f"Industry Map — {d['industry']}  ({d['n']} companies)", "=" * 74]
    if foc:
        L.append(f"Focus: {foc} (marked ►).  Ranked by market cap.")

    # Header
    L.append(f"  {'Ticker':<6}{'MktCap':>8}{'Rev':>7}{'RevCAGR':>8}"
             f"{'OpMgn':>7}{'NetMgn':>7}{'ROE':>6}{'P/E':>6}{'EV/EBITDA':>10}{'P/B':>6}")
    L.append("  " + "-" * 72)
    for r in d["companies"]:
        L.append(
            f"  {_name(r, foc)}{_money(r['market_cap']):>8}{_money(r['revenue']):>7}"
            f"{_pct(r['rev_cagr']):>8}{_pct(r['op_margin']):>7}{_pct(r['net_margin']):>7}"
            f"{_pct(r['roe']):>6}{_x(r['pe']):>6}{_x(r['ev_ebitda']):>10}{_x(r['pb']):>6}"
        )
    m = d["medians"]
    L.append("  " + "-" * 72)
    L.append(
        f"  {'MEDIAN':<6}{_money(m['market_cap']):>8}{_money(m['revenue']):>7}"
        f"{_pct(m['rev_cagr']):>8}{_pct(m['op_margin']):>7}{_pct(m['net_margin']):>7}"
        f"{_pct(m['roe']):>6}{_x(m['pe']):>6}{_x(m['ev_ebitda']):>10}{_x(m['pb']):>6}"
    )

    # Leaders
    lead = d["leaders"]
    def who(key, fmt, field):
        r = lead.get(key)
        return f"{r['ticker']} ({fmt(r[field])})" if r else "-"
    L.append("\nWho leads on what:")
    L.append(f"  Largest          {who('largest', _money, 'market_cap')}")
    L.append(f"  Fastest-growing  {who('fastest_growing', _pct, 'rev_cagr')}  (revenue CAGR)")
    L.append(f"  Most profitable  {who('most_profitable', _pct, 'net_margin')}  (net margin)")
    L.append(f"  Highest ROE      {who('highest_roe', _pct, 'roe')}")
    L.append(f"  Cheapest P/E     {who('cheapest_pe', _x, 'pe')}")
    L.append(f"  Cheapest EV/EBITDA {who('cheapest_ev', _x, 'ev_ebitda')}")
    L.append(f"  Richest P/E      {who('richest_pe', _x, 'pe')}")

    # Where the focus company sits vs its peers
    if foc:
        fr = next((r for r in d["companies"] if r["name"] == foc), None)
        if fr:
            L.append(f"\n{fr['ticker']} vs peers (median):")
            L.append(_rel_line("Revenue growth", fr["rev_cagr"], m["rev_cagr"], _pct, higher_better=True))
            L.append(_rel_line("Net margin",     fr["net_margin"], m["net_margin"], _pct, higher_better=True))
            L.append(_rel_line("ROE",            fr["roe"], m["roe"], _pct, higher_better=True))
            L.append(_rel_line("P/E",            fr["pe"], m["pe"], _x, higher_better=False))
            L.append(_rel_line("EV/EBITDA",      fr["ev_ebitda"], m["ev_ebitda"], _x, higher_better=False))

    L.append("\nFundamentals (growth/margins/ROE) are from EDGAR statements; multiples "
             "(P/E, P/S, EV/EBITDA, P/B) are the current Yahoo snapshot. '-' = data "
             "not available (e.g. foreign/ADR names have no stored 10-K).")
    return "\n".join(L)


def _rel_line(label, val, med, fmt, higher_better):
    if not isinstance(val, (int, float)) or not isinstance(med, (int, float)):
        return f"  {label:<15} {fmt(val):>7}   (peer median {fmt(med)})"
    above = val > med
    # For "higher is better" metrics above-median is good; for multiples (cheap
    # is good) below-median is the attractive side.
    good = (above == higher_better)
    if label in ("P/E", "EV/EBITDA"):
        verdict = "cheaper than peers" if not above else "richer than peers"
    else:
        verdict = "ahead of peers" if above else "behind peers"
    tag = "✓" if good else "•"
    return f"  {tag} {label:<13} {fmt(val):>7}   vs median {fmt(med):>6}  → {verdict}"


def main():
    ap = argparse.ArgumentParser(description="Industry peer-comparison (read-only)")
    ap.add_argument("--db", default=store.DB_PATH)
    ap.add_argument("--industry", help="industry name (exact or partial)")
    ap.add_argument("--company", help="map every industry this company belongs to")
    ap.add_argument("--json", action="store_true", help="emit raw JSON")
    args = ap.parse_args()

    if not args.industry and not args.company:
        ap.error("give --industry or --company")

    db = store.get_db(args.db)
    tgts = targets(db, args)
    if not tgts:
        q = args.industry or args.company
        print(f"Nothing to map for '{q}' in {args.db}", file=sys.stderr)
        sys.exit(1)

    results = [map_industry(db, ind, focus) for ind, focus in tgts]
    if args.json:
        print(json.dumps(results if len(results) > 1 else results[0], indent=2))
    else:
        print("\n\n".join(format_report(r) for r in results))
    db.close()


if __name__ == "__main__":
    main()
