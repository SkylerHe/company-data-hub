#!/usr/bin/env python3
"""
scrape_ibkr_options.py — real-time option chain (implied vol + Greeks) from IBKR.

Pulls live option quotes for an underlying + expiration straight from IB Gateway's
model, and stores each pull as a timestamped snapshot in `option_quotes`. Over time
those snapshots build the IV history that IV Rank / IV Percentile need.

IBKR's model reports implied vol + delta/gamma/vega/theta + the underlying price
(`modelGreeks`), but NOT rho — so rho is filled locally with volatility.bs_greeks()
using IBKR's own IV and spot, keeping every stored row complete.

Requirements (same as scrape_ibkr.py):
- IBKR account (paper or live) with an options market-data subscription
- IB Gateway or TWS running locally (Gateway paper: 4001)
- ib_insync:  pip install ib_insync

IMPORTANT: IB Gateway runs on YOUR machine. Run this locally, not in a cloud
session that can't reach localhost:4001.

Usage:
    # Strikes automatically chosen around the money (±`--num` strikes, both C & P):
    python scrape_ibkr_options.py --company QQQ --expiry 2026-08-20

    # Explicit strikes / rights:
    python scrape_ibkr_options.py --company QQQ --expiry 2026-08-20 \
                                  --strikes 713,748,754 --rights CP

    # Delayed data (no live options subscription):
    python scrape_ibkr_options.py --company QQQ --expiry 2026-08-20 --delayed
"""

import argparse
import sys
from datetime import date, datetime

try:
    from ib_insync import IB, Stock, Option
except ImportError:
    print("Error: ib_insync not installed — pip install ib_insync")
    sys.exit(1)

import store
import volatility

# IB Gateway connection (mirrors scrape_ibkr.py; distinct CLIENT_ID so both can run).
IBKR_HOST = "127.0.0.1"
IBKR_PORT = 4001          # Gateway paper: 4001 (live 4002, TWS 7496/7497)
CLIENT_ID = 7            # scrape_ibkr.py uses 1 — keep options on its own id


def connect_ibkr(delayed=False):
    ib = IB()
    try:
        ib.connect(IBKR_HOST, IBKR_PORT, clientId=CLIENT_ID, timeout=10)
        print(f"✓ Connected to IBKR at {IBKR_HOST}:{IBKR_PORT}")
    except Exception as e:
        print(f"✗ Failed to connect to IBKR: {e}")
        print("  Make sure IB Gateway/TWS is running (Gateway paper: localhost:4001).")
        sys.exit(1)
    # Market-data type: 1=live, 3=delayed, 4=delayed-frozen. Delayed still carries
    # the model Greeks, just lagged — fine for learning without a live subscription.
    ib.reqMarketDataType(3 if delayed else 1)
    return ib


def _norm_expiry(s):
    """Accept 'YYYY-MM-DD' or 'YYYYMMDD'; return (ib_fmt 'YYYYMMDD', iso 'YYYY-MM-DD')."""
    s = s.strip().replace("-", "")
    if len(s) != 8 or not s.isdigit():
        raise ValueError(f"bad --expiry {s!r}; use YYYY-MM-DD or YYYYMMDD")
    return s, f"{s[:4]}-{s[4:6]}-{s[6:]}"


def _wait_greeks(ib, ticker, timeout=6.0):
    """Give IB a moment to stream model Greeks back for a ticker."""
    waited = 0.0
    while ticker.modelGreeks is None and waited < timeout:
        ib.sleep(0.25)
        waited += 0.25
    return ticker.modelGreeks


def choose_strikes(chain, spot, num):
    """The `num` listed strikes nearest to spot."""
    strikes = sorted(chain.strikes)
    return sorted(strikes, key=lambda k: abs(k - spot))[:num]


def scrape_options(ib, db, company, expiry_arg, strikes=None, rights="CP",
                   num=6, source="IBKR"):
    ib_expiry, iso_expiry = _norm_expiry(expiry_arg)
    name = store.resolve_instrument(db, company) or company

    # Resolve the underlying and read its live price.
    stock = Stock(company if len(company) <= 5 else "", "SMART", "USD")
    # Prefer the stored ticker for the contract lookup.
    tkr = db.execute("SELECT ticker FROM instruments WHERE name=? OR ticker=?",
                     (name, company)).fetchone()
    symbol = (tkr[0] if tkr else company)
    stock = Stock(symbol, "SMART", "USD")
    if not ib.qualifyContracts(stock):
        print(f"✗ Could not qualify underlying {symbol}")
        return 0
    ustk = ib.reqMktData(stock, "", False, False)
    ib.sleep(2)
    spot = ustk.marketPrice() or ustk.last or ustk.close
    if not spot or spot != spot:            # None or NaN
        print("✗ No underlying price yet (market closed? try --delayed).")
        return 0
    print(f"  {symbol} spot ≈ {spot:.2f}")

    # Option-chain metadata (available strikes/expiries for this underlying).
    chains = ib.reqSecDefOptParams(stock.symbol, "", stock.secType, stock.conId)
    chain = next((c for c in chains if c.exchange == "SMART"), chains[0] if chains else None)
    if chain is None:
        print("✗ No option chain returned.")
        return 0
    if ib_expiry not in chain.expirations:
        print(f"  ! {iso_expiry} not in listed expirations; requesting anyway.")

    if strikes is None:
        strikes = choose_strikes(chain, spot, num)
    rights = [r for r in rights.upper() if r in ("C", "P")]
    print(f"  strikes: {', '.join(f'{k:g}' for k in strikes)}   rights: {'/'.join(rights)}")

    days = max((datetime.strptime(iso_expiry, "%Y-%m-%d").date() - date.today()).days, 0)
    snap = store._now()
    stored = 0

    for k in strikes:
        for r in rights:
            opt = Option(symbol, ib_expiry, k, r, "SMART", tradingClass=chain.tradingClass)
            if not ib.qualifyContracts(opt):
                print(f"    ! could not qualify {symbol} {iso_expiry} {k:g}{r}")
                continue
            t = ib.reqMktData(opt, "106", False, False)   # 106 = option implied vol
            mg = _wait_greeks(ib, t)
            iv = mg.impliedVol if mg else None
            und = (mg.undPrice if mg and mg.undPrice else spot)
            # IB gives IV + delta/gamma/vega/theta; compute rho ourselves to complete the row.
            rho = None
            if iv and und and days > 0:
                g = volatility.bs_greeks(und, k, days / 365.0, iv, right=("call" if r == "C" else "put"))
                rho = g["rho"]
            store.add_option_quote(
                db, name, iso_expiry, k, r,
                bid=_num(t.bid), ask=_num(t.ask), last=_num(t.last),
                underlying_price=und, implied_vol=iv,
                delta=(mg.delta if mg else None), gamma=(mg.gamma if mg else None),
                vega=(mg.vega if mg else None), theta=(mg.theta if mg else None),
                rho=rho, model_price=(mg.optPrice if mg else None),
                source=source, snapshot_at=snap,
            )
            ivtxt = f"{iv*100:5.1f}%" if iv else "  n/a"
            print(f"    {k:>7g}{r}  IV {ivtxt}  Δ {_fmt(mg.delta if mg else None)}")
            stored += 1
            ib.cancelMktData(opt)

    ib.cancelMktData(stock)
    return stored


def _num(x):
    """IB uses NaN/-1 for 'no quote'; normalize to None."""
    if x is None or (isinstance(x, float) and x != x) or x < 0:
        return None
    return x


def _fmt(x):
    return f"{x:+.3f}" if isinstance(x, (int, float)) and x == x else "  n/a"


def main():
    ap = argparse.ArgumentParser(description="Real-time IBKR option chain → option_quotes")
    ap.add_argument("--db", default=store.DB_PATH)
    ap.add_argument("--company", required=True, help="Underlying name or ticker (e.g. QQQ)")
    ap.add_argument("--expiry", required=True, help="Expiration YYYY-MM-DD or YYYYMMDD")
    ap.add_argument("--strikes", help="Comma list, e.g. 713,748,754 (default: around the money)")
    ap.add_argument("--rights", default="CP", help="Which rights: C, P, or CP (default CP)")
    ap.add_argument("--num", type=int, default=6, help="How many near-money strikes if --strikes omitted")
    ap.add_argument("--delayed", action="store_true", help="Use delayed data (no live subscription)")
    args = ap.parse_args()

    db = store.get_db(args.db)
    store.init_db(db)          # ensure option_quotes exists (idempotent)

    strikes = None
    if args.strikes:
        strikes = [float(s) for s in args.strikes.split(",") if s.strip()]

    ib = connect_ibkr(delayed=args.delayed)
    try:
        print(f"\n{args.company}  {args.expiry}")
        n = scrape_options(ib, db, args.company, args.expiry,
                           strikes=strikes, rights=args.rights, num=args.num)
        print(f"\n✓ Stored {n} option quotes into option_quotes (snapshot).")
    finally:
        ib.disconnect()


if __name__ == "__main__":
    main()
