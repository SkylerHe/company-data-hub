#!/usr/bin/env python3
"""
analyze.py — fundamental analysis engine (read-only over finance.db).

Turns the raw numbers other scripts collected into the things a value/growth
investor actually reads: multi-year margins and returns, a common-size income
statement, liquidity/solvency/efficiency ratios, growth rates, and
quality-of-earnings flags. It computes; it does not judge — the read-fundamentals
skill adds interpretation and teaching notes on top.

Two data sources, kept distinct on purpose:
  - SEC/EDGAR series  → multi-year *trend* (period 'FY2024', 'FY2023', …)
  - Yahoo snapshot     → *current* market-linked ratios EDGAR can't give from
                         statements alone (gross margin, quick ratio, P/E,
                         debt/equity). Dated one day (e.g. '2026-07-01').

Pure stdlib. No writes.

    python analyze.py --company Microsoft
    python analyze.py --company MSFT           # ticker also works
    python analyze.py --company Microsoft --json
"""

import argparse
import json
import sys

import store

EDGAR = "SEC/EDGAR"


# ----------------------------------------------------------------------------
# Data access
# ----------------------------------------------------------------------------
def resolve_company(db, query: str):
    """Return the instrument `name` for a name or ticker query, else None."""
    row = db.execute(
        "SELECT name FROM instruments WHERE name = ? OR ticker = ? LIMIT 1",
        (query, query),
    ).fetchone()
    if row:
        return row[0]
    row = db.execute(
        "SELECT name FROM instruments WHERE name LIKE ? LIMIT 1", (f"%{query}%",)
    ).fetchone()
    return row[0] if row else None


def series(db, company: str, metric: str, source: str = EDGAR) -> dict:
    """{period: value} for one metric from one source, ordered by period.
    Periods are 'FY####' so lexical order == chronological order."""
    rows = db.execute(
        """
        SELECT period, value FROM metrics m
        JOIN instruments i ON i.id = m.company_id
        WHERE i.name = ? AND m.metric = ? AND m.source = ? AND value IS NOT NULL
        ORDER BY period
        """,
        (company, metric, source),
    ).fetchall()
    return {p: v for p, v in rows}


def snapshot(db, company: str, metric: str) -> float | None:
    """Latest snapshot value for a metric.

    Prefers a Finviz value over Yahoo when one exists: Finviz is our correction
    layer for the fields Yahoo serves corrupt (book_value_per_share, pb_ratio,
    ev_ebitda — see scrape_finviz.py). Finviz only writes that narrow set, so for
    every other metric this transparently falls back to the newest Yahoo row.
    """
    row = db.execute(
        """
        SELECT value FROM metrics m
        JOIN instruments i ON i.id = m.company_id
        WHERE i.name = ? AND m.metric = ? AND m.source IN ('Finviz', 'Yahoo')
        ORDER BY CASE m.source WHEN 'Finviz' THEN 0 ELSE 1 END, period DESC
        LIMIT 1
        """,
        (company, metric),
    ).fetchone()
    return row[0] if row else None


# ----------------------------------------------------------------------------
# Math helpers
# ----------------------------------------------------------------------------
def _div(a, b):
    try:
        return a / b if (a is not None and b not in (None, 0)) else None
    except (TypeError, ZeroDivisionError):
        return None


def _ratio_series(num: dict, den: dict) -> dict:
    """Elementwise num[p]/den[p] over shared periods."""
    return {p: _div(num[p], den.get(p)) for p in num if den.get(p) not in (None, 0)}


def _cagr(s: dict):
    """Compound annual growth over a period-keyed series. None if signs make it
    meaningless (e.g. crossing zero)."""
    if len(s) < 2:
        return None
    vals = [s[p] for p in sorted(s)]
    first, last, n = vals[0], vals[-1], len(vals) - 1
    if first is None or last is None or first <= 0 or last <= 0:
        return None
    return (last / first) ** (1 / n) - 1


def _trend(s: dict) -> str:
    """Coarse direction of a series' last-vs-first."""
    vals = [s[p] for p in sorted(s) if s[p] is not None]
    if len(vals) < 2:
        return "n/a"
    if vals[-1] > vals[0] * 1.02:
        return "rising"
    if vals[-1] < vals[0] * 0.98:
        return "falling"
    return "flat"


# ----------------------------------------------------------------------------
# Analysis
# ----------------------------------------------------------------------------
def fundamentals(db, company: str) -> dict:
    """Assemble the full fundamental picture for one company."""
    g = lambda m: series(db, company, m)  # noqa: E731  EDGAR series shorthand

    revenue      = g("revenue")
    op_income    = g("operating_income")
    net_income   = g("net_income")
    fcf          = g("free_cash_flow")
    ocf          = g("operating_cash_flow")
    capex        = g("capital_expenditures")
    assets       = g("total_assets")
    liabilities  = g("total_liabilities")
    equity       = g("total_equity")
    cur_assets   = g("current_assets")
    cur_liab     = g("current_liabilities")
    shares       = g("shares_diluted")

    periods = sorted(revenue)

    margins = {
        "operating_margin": _ratio_series(op_income, revenue),
        "net_margin":       _ratio_series(net_income, revenue),
        "fcf_margin":       _ratio_series(fcf, revenue),
    }
    returns = {
        "roa": _ratio_series(net_income, assets),
        "roe": _ratio_series(net_income, equity),
    }
    liquidity = {
        "current_ratio": _ratio_series(cur_assets, cur_liab),
    }
    solvency = {
        "liabilities_to_equity": _ratio_series(liabilities, equity),
        "liabilities_to_assets": _ratio_series(liabilities, assets),
        "equity_ratio":          _ratio_series(equity, assets),
    }
    efficiency = {
        "asset_turnover": _ratio_series(revenue, assets),
    }
    growth = {
        "revenue_cagr":    _cagr(revenue),
        "net_income_cagr": _cagr(net_income),
        "fcf_cagr":        _cagr(fcf),
        "equity_cagr":     _cagr(equity),
    }

    # Quality-of-earnings flags — each is a small verdict on one dimension.
    quality = []
    cash_conv = _ratio_series(fcf, net_income)
    if cash_conv:
        latest = cash_conv[sorted(cash_conv)[-1]]
        quality.append({
            "flag": "cash_conversion (FCF / net income)",
            "latest": latest,
            "trend": _trend(cash_conv),
            "read": "healthy (>0.8): earnings are cash-backed"
                    if latest and latest >= 0.8 else
                    "watch (<0.8): profit not fully converting to cash",
        })
    accruals = {p: _div((net_income.get(p, 0) - ocf.get(p, 0)), assets.get(p))
                for p in periods if assets.get(p)}
    if accruals:
        latest = accruals[sorted(accruals)[-1]]
        quality.append({
            "flag": "accrual ratio ((NI − OCF) / assets)",
            "latest": latest,
            "trend": _trend(accruals),
            "read": "low is good; high/positive means earnings lean on accruals, "
                    "not cash",
        })
    if shares and len(shares) >= 2:
        sv = [shares[p] for p in sorted(shares)]
        chg = _div(sv[-1] - sv[0], sv[0])
        quality.append({
            "flag": "share count (dilution)",
            "latest": chg,
            "trend": _trend(shares),
            "read": "shrinking share count (buybacks) is shareholder-friendly; "
                    "rising = dilution",
        })
    capex_int = _ratio_series(capex, revenue)
    if capex_int:
        latest = capex_int[sorted(capex_int)[-1]]
        quality.append({
            "flag": "capex intensity (capex / revenue)",
            "latest": latest,
            "trend": _trend(capex_int),
            "read": "rising intensity = heavier reinvestment; weigh against "
                    "revenue growth it buys",
        })

    # Current market-linked ratios EDGAR statements can't give on their own.
    snap = {m: snapshot(db, company, m) for m in (
        "gross_margin", "quick_ratio", "debt_to_equity", "pe_ratio",
        "forward_pe", "peg_ratio", "ps_ratio", "pb_ratio", "ev_ebitda",
        "roe", "dividend_yield", "beta", "market_cap",
    )}

    return {
        "company": company,
        "periods": periods,
        "statement": {
            "revenue": revenue, "operating_income": op_income,
            "net_income": net_income, "free_cash_flow": fcf,
            "total_assets": assets, "total_equity": equity,
        },
        "common_size_income": {  # each line as % of revenue
            "operating_income": _ratio_series(op_income, revenue),
            "net_income":       _ratio_series(net_income, revenue),
            "free_cash_flow":   _ratio_series(fcf, revenue),
        },
        "margins": margins,
        "returns": returns,
        "liquidity": liquidity,
        "solvency": solvency,
        "efficiency": efficiency,
        "growth": growth,
        "quality": quality,
        "snapshot": snap,
    }


# ----------------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------------
def _pct(x):
    return f"{x*100:5.1f}%" if isinstance(x, (int, float)) else "   -  "


def _num(x):
    return f"{x:5.2f}" if isinstance(x, (int, float)) else "  -  "


def format_report(d: dict) -> str:
    periods = d["periods"]
    if not periods:
        return (f"No EDGAR statement history for {d['company']}. "
                f"Run: python scrape_edgar_financials.py --company \"{d['company']}\"")
    L = [f"Fundamentals — {d['company']}", "=" * 60,
         "Fiscal years: " + ", ".join(periods), ""]

    def row(label, s, fmt=_pct):
        cells = " ".join(fmt(s.get(p)) for p in periods)
        L.append(f"  {label:<22} {cells}")

    L.append("Revenue ($B):")
    row("revenue", {p: v/1e9 for p, v in d["statement"]["revenue"].items()}, _num)
    L.append("\nProfitability (margins):")
    row("operating margin", d["margins"]["operating_margin"])
    row("net margin", d["margins"]["net_margin"])
    row("FCF margin", d["margins"]["fcf_margin"])
    L.append("\nReturns:")
    row("ROE", d["returns"]["roe"])
    row("ROA", d["returns"]["roa"])
    L.append("\nLiquidity / Solvency:")
    row("current ratio", d["liquidity"]["current_ratio"], _num)
    row("liabilities/equity", d["solvency"]["liabilities_to_equity"], _num)
    row("equity ratio", d["solvency"]["equity_ratio"])
    L.append("\nEfficiency:")
    row("asset turnover", d["efficiency"]["asset_turnover"], _num)

    L.append("\nGrowth (CAGR over the window):")
    for k, v in d["growth"].items():
        L.append(f"  {k:<22} {_pct(v)}")

    L.append("\nQuality of earnings:")
    for q in d["quality"]:
        val = q["latest"]
        vs = _pct(val) if q["flag"].startswith(("cash", "accrual", "share", "capex")) else _num(val)
        L.append(f"  • {q['flag']}: {vs.strip()} ({q['trend']})")
        L.append(f"      {q['read']}")

    # Yahoo snapshot values use mixed scaling (margins/ROE/yield in percent-form,
    # multiples as plain numbers) and occasional bad points, so print them
    # as-stored rather than fabricating unit symbols.
    L.append("\nCurrent market ratios (Yahoo snapshot, as-stored):")
    snap = d["snapshot"]
    for k in ("pe_ratio", "forward_pe", "peg_ratio", "ps_ratio", "pb_ratio",
              "ev_ebitda", "gross_margin", "debt_to_equity", "dividend_yield", "beta"):
        v = snap.get(k)
        if v is not None:
            L.append(f"  {k:<16} {v:.2f}")
    return "\n".join(L)


# ----------------------------------------------------------------------------
# Common-size view (reads the materialized common_size table)
# ----------------------------------------------------------------------------
_CS_TITLE = {
    "income":    "Income statement (% of revenue)",
    "balance":   "Balance sheet (% of total assets)",
    "cash_flow": "Cash flow (% of revenue)",
}
_CS_ORDER = {
    "income":    ["revenue", "operating_income", "net_income"],
    "balance":   ["total_assets", "current_assets", "total_liabilities",
                  "current_liabilities", "total_equity"],
    "cash_flow": ["operating_cash_flow", "capital_expenditures", "free_cash_flow"],
}
_CS_LABEL = {
    "revenue": "Revenue", "operating_income": "Operating income",
    "net_income": "Net income", "total_assets": "Total assets",
    "current_assets": "Current assets", "total_liabilities": "Total liabilities",
    "current_liabilities": "Current liabilities", "total_equity": "Total equity",
    "operating_cash_flow": "Operating cash flow",
    "capital_expenditures": "Capital expenditures", "free_cash_flow": "Free cash flow",
}


def common_size_view(db, company):
    """Nested {statement: {line_item: {period: pct}}} + sorted periods, from the table."""
    data, periods = {}, set()
    for stmt, item, period, pct, _base in store.get_common_size(db, company):
        data.setdefault(stmt, {}).setdefault(item, {})[period] = pct
        periods.add(period)
    return data, sorted(periods)


def format_common_size(company, data, periods) -> str:
    if not periods:
        return (f"No common-size data for {company}. Populate it with:\n"
                f"  python scrape_edgar_financials.py --company \"{company}\"\n"
                f"  python store.py --recompute-common-size")
    L = [f"Common-size statements — {company}", "=" * 60,
         "Fiscal years: " + ", ".join(periods),
         "Each line = % of its base (income/cash-flow ÷ revenue, balance ÷ assets).", ""]
    for stmt in ("income", "balance", "cash_flow"):
        if stmt not in data:
            continue
        L.append(_CS_TITLE[stmt] + ":")
        order = _CS_ORDER[stmt]
        items = [i for i in order if i in data[stmt]] + \
                [i for i in data[stmt] if i not in order]
        for item in items:
            s = data[stmt][item]
            cells = " ".join(_pct(s.get(p)) for p in periods)
            L.append(f"  {_CS_LABEL.get(item, item):<22} {cells}")
        L.append("")
    return "\n".join(L).rstrip()


def main():
    ap = argparse.ArgumentParser(description="Fundamental analysis (read-only)")
    ap.add_argument("--db", default=store.DB_PATH)
    ap.add_argument("--company", required=True, help="company name or ticker")
    ap.add_argument("--common-size", dest="common_size", action="store_true",
                    help="print the multi-year common-size statements (from common_size)")
    ap.add_argument("--json", action="store_true", help="emit raw JSON")
    args = ap.parse_args()

    db = store.get_db(args.db)
    name = resolve_company(db, args.company)
    if not name:
        print(f"'{args.company}' not found in {args.db}", file=sys.stderr)
        sys.exit(1)

    if args.common_size:
        cs, periods = common_size_view(db, name)
        if args.json:
            print(json.dumps({"company": name, "periods": periods, "common_size": cs}, indent=2))
        else:
            print(format_common_size(name, cs, periods))
        db.close()
        return

    data = fundamentals(db, name)
    print(json.dumps(data, indent=2) if args.json else format_report(data))
    db.close()


if __name__ == "__main__":
    main()
