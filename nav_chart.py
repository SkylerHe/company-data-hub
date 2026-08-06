#!/usr/bin/env python3
"""nav_chart.py — plot account Net Asset Value (NAV) vs a benchmark index.

Reads two series from finance.db, rebases BOTH to 100 at their first common date
(so you compare *performance*, not dollar levels), and writes a self-contained SVG.

Series source by instrument type:
  * account pseudo-instrument (PORTFOLIO) -> the `netliquidation` metric time-series
  * anything else (SPY, QQQ, a stock)     -> the `prices.close` series

Usage:
  python nav_chart.py                                  # PORTFOLIO vs SPY
  python nav_chart.py --account PORTFOLIO --benchmark QQQ
  python nav_chart.py --account QQQ --benchmark SPY     # demo with two real series
  python nav_chart.py --out ~/Desktop/nav.svg
"""
import argparse
import datetime as _dt
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
os.chdir(REPO)                       # store.DB_PATH is CWD-relative
import store  # noqa: E402

W, H = 900, 460                      # SVG canvas
PAD_L, PAD_R, PAD_T, PAD_B = 60, 130, 40, 46
PLOT_W, PLOT_H = W - PAD_L - PAD_R, H - PAD_T - PAD_B


def load_series(db, instrument):
    """Return [(date_str, value), ...] ascending, for an account or a priced instrument."""
    row = db.execute(
        "SELECT id, asset_class FROM instruments WHERE ticker=? OR name=?",
        (instrument, instrument)).fetchone()
    if not row:
        return []
    iid, ac = row
    if ac == "account":
        rows = db.execute(
            "SELECT period, value FROM metrics WHERE company_id=? AND metric='netliquidation' "
            "AND value IS NOT NULL ORDER BY period", (iid,)).fetchall()
    else:
        rows = db.execute(
            "SELECT date, close FROM prices WHERE instrument_id=? AND close IS NOT NULL "
            "ORDER BY date", (iid,)).fetchall()
    return [(r[0], float(r[1])) for r in rows]


def _ord(d):
    return _dt.date.fromisoformat(d).toordinal()


def rebase_common(a, b):
    """Clip both series to their overlapping date window and rebase each to 100 at the
    first in-window point. Returns (a2, b2) as [(date, rebased_value)]."""
    if not a or not b:
        return [], []
    lo = max(a[0][0], b[0][0])
    hi = min(a[-1][0], b[-1][0])
    a = [(d, v) for d, v in a if lo <= d <= hi]
    b = [(d, v) for d, v in b if lo <= d <= hi]
    if not a or not b:
        return [], []
    a0, b0 = a[0][1], b[0][1]
    return ([(d, v / a0 * 100) for d, v in a],
            [(d, v / b0 * 100) for d, v in b])


def _poly(series, x0, x1, ymin, ymax, color):
    span = (x1 - x0) or 1
    pts = []
    for d, v in series:
        x = PAD_L + (_ord(d) - x0) / span * PLOT_W
        y = PAD_T + (ymax - v) / (ymax - ymin) * PLOT_H
        pts.append(f"{x:.1f},{y:.1f}")
    return (f'<polyline fill="none" stroke="{color}" stroke-width="2.2" '
            f'stroke-linejoin="round" points="{" ".join(pts)}"/>')


def render_svg(name_a, sa, name_b, sb):
    x0 = _ord(min(sa[0][0], sb[0][0]))
    x1 = _ord(max(sa[-1][0], sb[-1][0]))
    vals = [v for _, v in sa] + [v for _, v in sb]
    ymin, ymax = min(vals), max(vals)
    pad = (ymax - ymin) * 0.08 or 1
    ymin, ymax = ymin - pad, ymax + pad

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
             f'font-family="-apple-system,Segoe UI,Roboto,sans-serif">',
             f'<rect width="{W}" height="{H}" fill="#ffffff"/>']
    # y gridlines (rebased = 100 baseline emphasized)
    for gv in _nice_ticks(ymin, ymax):
        y = PAD_T + (ymax - gv) / (ymax - ymin) * PLOT_H
        emph = abs(gv - 100) < 1e-6
        parts.append(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{PAD_L+PLOT_W}" y2="{y:.1f}" '
                     f'stroke="{"#bbb" if emph else "#ececec"}" stroke-width="1" '
                     f'{"stroke-dasharray=\"4 4\"" if emph else ""}/>')
        parts.append(f'<text x="{PAD_L-8}" y="{y+4:.1f}" text-anchor="end" font-size="11" '
                     f'fill="#888">{gv:.0f}</text>')
    # x end-date labels
    for d, anch, xx in [(sa[0][0], "start", PAD_L), (sa[-1][0], "end", PAD_L+PLOT_W)]:
        parts.append(f'<text x="{xx}" y="{H-PAD_B+22}" text-anchor="{"start" if anch=="start" else "end"}" '
                     f'font-size="11" fill="#888">{d}</text>')
    # the two lines
    cA, cB = "#2f6f4f", "#c47a2f"
    parts.append(_poly(sa, x0, x1, ymin, ymax, cA))
    parts.append(_poly(sb, x0, x1, ymin, ymax, cB))
    # end-value badges + legend
    for nm, s, c, dy in [(name_a, sa, cA, 0), (name_b, sb, cB, 22)]:
        endv = s[-1][1]
        parts.append(f'<rect x="{PAD_L+PLOT_W+14}" y="{PAD_T+dy}" width="10" height="10" fill="{c}"/>')
        parts.append(f'<text x="{PAD_L+PLOT_W+28}" y="{PAD_T+dy+9}" font-size="12" fill="#333">'
                     f'{nm}  <tspan font-weight="700" fill="{c}">{endv:.0f}</tspan></text>')
    # title
    winner = name_a if sa[-1][1] >= sb[-1][1] else name_b
    parts.append(f'<text x="{PAD_L}" y="24" font-size="14" font-weight="700" fill="#111">'
                 f'{name_a} vs {name_b} — rebased to 100 (both start equal)</text>')
    parts.append(f'<text x="{PAD_L}" y="{H-8}" font-size="11" fill="#888">'
                 f'higher line = better performance · leader: {winner}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def _nice_ticks(lo, hi, n=5):
    step = (hi - lo) / n
    mag = 10 ** (len(str(int(step))) - 1) if step >= 1 else 1
    step = max(1, round(step / mag) * mag)
    start = (int(lo) // int(step)) * int(step)
    return [start + i * step for i in range(n + 3) if lo <= start + i * step <= hi]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default="PORTFOLIO", help="account (NAV) or any instrument")
    ap.add_argument("--benchmark", default="SPY", help="benchmark index (SPY/QQQ/...)")
    ap.add_argument("--out", default="nav_vs_index.svg")
    args = ap.parse_args()

    db = store.get_db()
    a = load_series(db, args.account)
    b = load_series(db, args.benchmark)
    if len(a) < 2:
        print(f"! '{args.account}' has {len(a)} point(s) — need >=2 for a NAV curve.")
        print("  (The account records one netliquidation point per daily run; the curve")
        print("   builds up once the account scraper runs on a schedule.)")
        return
    if len(b) < 2:
        print(f"! benchmark '{args.benchmark}' has no price history."); return

    sa, sb = rebase_common(a, b)
    if not sa or not sb:
        print("! the two series don't overlap in time — no common window to compare."); return

    svg = render_svg(args.account, sa, args.benchmark, sb)
    with open(args.out, "w") as f:
        f.write(svg)
    ra, rb = sa[-1][1] - 100, sb[-1][1] - 100
    print(f"{args.account}: {ra:+.1f}%   {args.benchmark}: {rb:+.1f}%   "
          f"(over {sa[0][0]} → {sa[-1][0]})")
    print(f"✓ wrote {args.out}")


if __name__ == "__main__":
    main()
