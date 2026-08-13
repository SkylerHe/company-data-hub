#!/usr/bin/env python3
"""
volatility.py — volatility & option-Greeks engine (read-only, stdlib only).

Two jobs, both computable from data you already have or a single quoted price:

1. REALIZED (historical) volatility from the `prices` table — how much a name has
   ACTUALLY swung. Close-to-close log returns, annualized (×√252). This is the
   backward-looking twin of implied vol.

2. Black-Scholes pricing, the GREEKS (delta/gamma/vega/theta/rho), and an
   IMPLIED-VOL solver (price → the vol that reproduces it). Uses continuous
   dividend yield; European model — very close to IBKR's American values for
   not-deep-ITM options, and identical in the concepts.

Nothing here writes to the DB (analysis engines are read-only). To CAPTURE live
implied vol + Greeks from IBKR into the `option_quotes` table, use
`scrape_ibkr_options.py`, which reuses bs_greeks() below to fill rho.

Usage:
    # Realized vol from stored prices (name or ticker):
    python volatility.py --company QQQ

    # Greeks for an option at a known IV (what you'd read off IBKR):
    python volatility.py --greeks --spot 733.94 --strike 748 --days 7 \
                         --iv 19.05 --right call

    # Solve implied vol from a market price, then show the Greeks:
    python volatility.py --greeks --spot 733.94 --strike 748 --days 7 \
                         --price 1.47 --right call
"""

import argparse
import math
import sys
from collections import OrderedDict
from datetime import datetime, timedelta

import store

TRADING_DAYS = 252          # annualization factor for realized vol
DEFAULT_RATE = 0.05         # ~short T-bill rate, override with --rate
DEFAULT_DIV = 0.0           # dividend yield, override with --div


# ---------------------------------------------------------------------------
# Normal distribution (stdlib only — no scipy)
# ---------------------------------------------------------------------------
def _norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


# ---------------------------------------------------------------------------
# 1. Realized (historical) volatility from the prices table
# ---------------------------------------------------------------------------
def realized_vol(closes, window=None):
    """Annualized realized volatility from a list of closing prices.

    Uses close-to-close log returns; if `window` is given, only the last `window`
    returns are used. Returns a decimal (0.19 = 19%) or None if not enough data."""
    if window is not None:
        closes = closes[-(window + 1):]     # window returns need window+1 closes
    if len(closes) < 2:
        return None
    rets = [math.log(closes[i] / closes[i - 1])
            for i in range(1, len(closes)) if closes[i - 1] and closes[i]]
    n = len(rets)
    if n < 2:
        return None
    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / (n - 1)   # sample variance
    return math.sqrt(var) * math.sqrt(TRADING_DAYS)


def realized_vol_table(db, company, windows=(20, 30, 60, 90)):
    """Print annualized realized vol over several trailing windows for one name."""
    name = store.resolve_instrument(db, company)
    if not name:
        print(f"'{company}' not found in the database.")
        return
    rows = store.get_prices(db, name, field="close")
    closes = [c for _, c in rows if c is not None]
    if len(closes) < 21:
        print(f"{name}: not enough price history ({len(closes)} closes) for realized vol.")
        return
    spot = closes[-1]
    print(f"\nRealized (historical) volatility — {name}")
    print(f"  latest close: {spot:,.2f}   ({len(closes)} closes on file)")
    print("  " + "-" * 40)
    for w in windows:
        rv = realized_vol(closes, window=w)
        if rv is not None:
            print(f"  {w:>4}-day   {rv * 100:6.1f}%  annualized")
    full = realized_vol(closes)
    if full is not None:
        print(f"  full     {full * 100:6.1f}%  annualized  ({len(closes) - 1} returns)")
    print("  " + "-" * 40)
    print("  Compare these to an option's IMPLIED vol: implied > realized favors\n"
          "  SELLING premium; implied < realized favors BUYING it.\n")


# ---------------------------------------------------------------------------
# 1b. IV Rank / IV Percentile from the option_quotes history
# ---------------------------------------------------------------------------
def _atm_iv_history(db, underlying, expiry=None):
    """[(snapshot_at, atm_iv), ...] oldest→newest: one representative (at-the-money)
    implied vol per snapshot. ATM = the strike nearest that snapshot's underlying
    price (mean across call/put if both quoted). This is the series IV Rank ranks."""
    name = store.resolve_instrument(db, underlying)
    iid = store.company_id(db, name, create=False) if name else None
    if iid is None:
        return []
    q = ("SELECT snapshot_at, strike, implied_vol, underlying_price FROM option_quotes "
         "WHERE instrument_id=? AND implied_vol IS NOT NULL")
    args = [iid]
    if expiry:
        q += " AND expiry=?"; args.append(expiry)
    q += " ORDER BY snapshot_at"
    groups = OrderedDict()
    for sa, strike, iv, und in db.execute(q, args).fetchall():
        groups.setdefault(sa, []).append((strike, iv, und))
    hist = []
    for sa, items in groups.items():
        und = next((u for _, _, u in items if u), None)
        if und is not None:
            atm_strike = min(items, key=lambda t: abs(t[0] - und))[0]
        else:                                   # no spot on file → use the median strike
            strikes = sorted({s for s, _, _ in items})
            atm_strike = strikes[len(strikes) // 2]
        at = [iv for s, iv, _ in items if s == atm_strike]
        if at:
            hist.append((sa, sum(at) / len(at)))
    return hist


def iv_rank(db, underlying, expiry=None, lookback_days=252):
    """Where the LATEST implied vol sits vs. its own recent history.

    Returns a dict with current IV, the window low/high, IV Rank (0=low,100=high of
    the range) and IV Percentile (% of past snapshots below today), or None if there
    isn't enough history. Needs several snapshots from scrape_ibkr_options.py first."""
    hist = _atm_iv_history(db, underlying, expiry)
    if lookback_days and hist:
        cutoff = datetime.fromisoformat(hist[-1][0]) - timedelta(days=lookback_days)
        hist = [(sa, iv) for sa, iv in hist if datetime.fromisoformat(sa) >= cutoff]
    if len(hist) < 2:
        return None
    ivs = [iv for _, iv in hist]
    cur, lo, hi = ivs[-1], min(ivs), max(ivs)
    rank = (cur - lo) / (hi - lo) * 100 if hi > lo else None
    pct = sum(1 for v in ivs[:-1] if v < cur) / (len(ivs) - 1) * 100
    return {"current": cur, "low": lo, "high": hi, "rank": rank,
            "percentile": pct, "n": len(ivs)}


def iv_rank_report(db, underlying, expiry=None, lookback_days=252):
    r = iv_rank(db, underlying, expiry, lookback_days)
    name = store.resolve_instrument(db, underlying) or underlying
    if r is None:
        print(f"\n{name}: not enough option_quotes history for IV Rank yet.\n"
              f"  Capture snapshots over time with scrape_ibkr_options.py, then re-run.\n")
        return
    print(f"\nIV Rank — {name}" + (f"  ({expiry})" if expiry else ""))
    print(f"  snapshots used: {r['n']}   lookback: {lookback_days}d")
    print("  " + "-" * 44)
    print(f"  current ATM IV   {r['current'] * 100:6.1f}%")
    print(f"  range low/high   {r['low'] * 100:6.1f}%  /  {r['high'] * 100:5.1f}%")
    rank = f"{r['rank']:.0f}" if r["rank"] is not None else "n/a"
    print(f"  IV Rank          {rank:>6}   (0=cheapest, 100=richest in range)")
    print(f"  IV Percentile    {r['percentile']:6.0f}   (% of days below today)")
    print("  " + "-" * 44)
    if r["rank"] is not None:
        if r["rank"] >= 50:
            lean = "premium is RICH → lean toward SELLING options (collect, expect IV to fall)"
        else:
            lean = "premium is CHEAP → lean toward BUYING options (pay little, expect IV to rise)"
        print(f"  Read: {lean}\n  (volatility mean-reverts, which is why the lean has an edge)\n")


# ---------------------------------------------------------------------------
# 2. Black-Scholes price + Greeks + implied-vol solver
# ---------------------------------------------------------------------------
def bs_greeks(S, K, T, sigma, r=DEFAULT_RATE, q=DEFAULT_DIV, right="call"):
    """Black-Scholes price and Greeks for one option (continuous dividend yield q).

    Inputs: S spot, K strike, T years-to-expiry, sigma vol (decimal), r rate, q div.
    Returns a dict with price and the five Greeks in TRADER-FRIENDLY units:
        delta  — per $1 move in the underlying
        gamma  — change in delta per $1 move
        vega   — per +1 percentage-point of IV   (e.g. 19% -> 20%)
        theta  — per calendar day (usually negative)
        rho    — per +1 percentage-point of interest rate
    """
    call = right.lower().startswith("c")
    if T <= 0 or sigma <= 0:                         # degenerate: intrinsic only
        intrinsic = max(S - K, 0.0) if call else max(K - S, 0.0)
        return {"price": intrinsic, "delta": (1.0 if call else -1.0) if intrinsic > 0 else 0.0,
                "gamma": 0.0, "vega": 0.0, "theta": 0.0, "rho": 0.0}
    sqrtT = math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * sqrtT)
    d2 = d1 - sigma * sqrtT
    disc_q = math.exp(-q * T)
    disc_r = math.exp(-r * T)
    pdf_d1 = _norm_pdf(d1)

    # gamma and vega are the same for calls and puts
    gamma = disc_q * pdf_d1 / (S * sigma * sqrtT)
    vega_per_1vol = S * disc_q * pdf_d1 * sqrtT       # per 1.00 (=100 vol points)

    if call:
        price = S * disc_q * _norm_cdf(d1) - K * disc_r * _norm_cdf(d2)
        delta = disc_q * _norm_cdf(d1)
        theta_year = (-(S * disc_q * pdf_d1 * sigma) / (2 * sqrtT)
                      - r * K * disc_r * _norm_cdf(d2)
                      + q * S * disc_q * _norm_cdf(d1))
        rho_per_1rate = K * T * disc_r * _norm_cdf(d2)
    else:
        price = K * disc_r * _norm_cdf(-d2) - S * disc_q * _norm_cdf(-d1)
        delta = -disc_q * _norm_cdf(-d1)
        theta_year = (-(S * disc_q * pdf_d1 * sigma) / (2 * sqrtT)
                      + r * K * disc_r * _norm_cdf(-d2)
                      - q * S * disc_q * _norm_cdf(-d1))
        rho_per_1rate = -K * T * disc_r * _norm_cdf(-d2)

    return {
        "price": price,
        "delta": delta,
        "gamma": gamma,
        "vega": vega_per_1vol / 100.0,       # per +1 IV point
        "theta": theta_year / 365.0,         # per calendar day
        "rho": rho_per_1rate / 100.0,        # per +1% rate
    }


def implied_vol(price, S, K, T, r=DEFAULT_RATE, q=DEFAULT_DIV, right="call"):
    """Solve for the vol (decimal) that makes the BS price equal `price` (bisection)."""
    lo, hi = 1e-4, 5.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if bs_greeks(S, K, T, mid, r, q, right)["price"] > price:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def print_greeks(S, K, days, sigma, r, q, right):
    T = days / 365.0
    g = bs_greeks(S, K, T, sigma, r, q, right)
    label = "CALL" if right.lower().startswith("c") else "PUT"
    print(f"\n{label}  strike {K:g}  ·  {days:g} days  ·  spot {S:g}  ·  "
          f"IV {sigma * 100:.2f}%  (r={r*100:.1f}%, q={q*100:.1f}%)")
    print("  " + "-" * 46)
    print(f"  Fair value   {g['price']:>10.2f}   (per share; ×100 = per contract)")
    print(f"  Delta        {g['delta']:>10.4f}   per $1 move  (~prob. ITM)")
    print(f"  Gamma        {g['gamma']:>10.5f}   delta change per $1 move")
    print(f"  Vega         {g['vega']:>10.4f}   per +1 IV point")
    print(f"  Theta        {g['theta']:>10.4f}   per day  (decay)")
    print(f"  Rho          {g['rho']:>10.4f}   per +1% rate")
    print("  " + "-" * 46)


def main():
    ap = argparse.ArgumentParser(description="Realized volatility & option Greeks (read-only)")
    ap.add_argument("--db", default=store.DB_PATH)
    ap.add_argument("--company", help="Realized vol for this name/ticker (from prices)")
    ap.add_argument("--iv-rank", dest="iv_rank", help="IV Rank/Percentile for this name (from option_quotes)")
    ap.add_argument("--expiry", help="Restrict IV Rank to one expiry (YYYY-MM-DD)")
    ap.add_argument("--lookback", type=int, default=252, help="IV Rank lookback in days (default 252)")
    ap.add_argument("--greeks", action="store_true", help="Compute option price + Greeks")
    ap.add_argument("--spot", type=float, help="Underlying price S")
    ap.add_argument("--strike", type=float, help="Strike K")
    ap.add_argument("--days", type=float, help="Calendar days to expiration")
    ap.add_argument("--iv", type=float, help="Implied vol in PERCENT (e.g. 19.05)")
    ap.add_argument("--price", type=float, help="Option market price → solve IV, then Greeks")
    ap.add_argument("--right", default="call", choices=["call", "put"])
    ap.add_argument("--rate", type=float, default=DEFAULT_RATE * 100, help="Rate %% (default 5)")
    ap.add_argument("--div", type=float, default=DEFAULT_DIV * 100, help="Dividend yield %% (default 0)")
    args = ap.parse_args()

    if args.greeks:
        missing = [n for n in ("spot", "strike", "days") if getattr(args, n) is None]
        if missing or (args.iv is None and args.price is None):
            ap.error("--greeks needs --spot --strike --days and one of --iv / --price")
        r, q = args.rate / 100.0, args.div / 100.0
        T = args.days / 365.0
        if args.price is not None:
            sigma = implied_vol(args.price, args.spot, args.strike, T, r, q, args.right)
            print(f"\nSolved implied vol from price {args.price:g}: {sigma * 100:.2f}%")
        else:
            sigma = args.iv / 100.0
        print_greeks(args.spot, args.strike, args.days, sigma, r, q, args.right)
        return

    if args.iv_rank:
        db = store.get_db(args.db)
        iv_rank_report(db, args.iv_rank, expiry=args.expiry, lookback_days=args.lookback)
        return

    if args.company:
        db = store.get_db(args.db)
        realized_vol_table(db, args.company)
        return

    ap.print_help()


if __name__ == "__main__":
    main()
