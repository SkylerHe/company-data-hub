#!/usr/bin/env python3
"""
health_check.py - Full status check of every data source, with email alerting.

Checks each resource two ways:
  1. LIVE   - can we actually reach/authenticate the source right now?
  2. FRESH  - is the data in the DB recent enough (is extraction actually flowing)?

If ANY source fails either check, a warning email is sent to ALERT_EMAIL_TO.

Sources checked:
  IBKR      IB Gateway API on 127.0.0.1:4001   (prices)
  Finnhub   company-news API (needs FINNHUB_API_KEY)   (news)
  Yahoo     yfinance quote fetch                (fundamentals + prices)
  SEC       EDGAR reachability                  (filings)

Config (put in .env; .env is git-ignored):
  FINNHUB_API_KEY=...
  SMTP_USER=you@gmail.com            # gmail address that sends the alert
  SMTP_PASSWORD=xxxx xxxx xxxx xxxx  # gmail APP PASSWORD (not your login pw)
  ALERT_EMAIL_TO=skyleryh6km@gmail.com
  # optional: SMTP_HOST (default smtp.gmail.com), SMTP_PORT (default 465),
  #           ALERT_EMAIL_FROM (default = SMTP_USER)

Usage:
    python health_check.py               # check; email only if something is down
    python health_check.py --always-email  # email the report even if all OK
    python health_check.py --dry-run      # print the report; never send
"""

import argparse
import os
import smtplib
import socket
import ssl
import struct
import sys
from datetime import datetime, timezone, date
from email.message import EmailMessage

import store


def _load_dotenv(path=".env"):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


_load_dotenv()

# Max age (days) before data is considered stale / extraction "not working".
FRESH_LIMIT = {"prices": 2, "fundamentals": 16, "filings": 10, "news": 3}

# Account NAV is recorded once per day by run_daily.sh (scrape_ibkr_account.py
# --account), which needs IB Gateway. A single missed day is normal - the gateway is
# flaky and IBKR *connectivity* failures never alert. But a MULTI-DAY gap is not
# flakiness, it is a broken pipeline, and it silently destroys the NAV-vs-index
# history that nav_chart.py and any drawdown/Sharpe work depend on. This threshold
# is what separates the two.
NAV_STALE_DAYS = 7
DEFAULT_ALERT_TO = "skyleryh6km@gmail.com"


def _age_days(iso_ts):
    if not iso_ts:
        return None
    dt = datetime.fromisoformat(iso_ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0


# ---------------------------------------------------------------- live checks
def check_ibkr():
    """IB Gateway up AND logged in, via the raw IB API handshake.

    We deliberately avoid ib_insync's connect(), whose mandatory account/position
    sync hangs on this gateway and produces false negatives. The handshake below
    (send 'API\\0' + version range, read back the server version) confirms the API
    server is alive and authenticated without touching account data.
    """
    try:
        s = socket.create_connection(("127.0.0.1", 4001), timeout=4)
    except OSError as e:
        return False, f"port 4001 not reachable ({e.__class__.__name__}) — is IB Gateway running?"
    try:
        s.settimeout(4)
        s.sendall(b"API\x00")
        payload = b"v100..178"
        s.sendall(struct.pack("!I", len(payload)) + payload)
        hdr = s.recv(4)
        if len(hdr) < 4:
            return False, "no API handshake response — Gateway logged out or API disabled"
        n = struct.unpack("!I", hdr)[0]
        data = s.recv(n)
        parts = data.split(b"\x00")
        return True, f"logged in (API server v{parts[0].decode(errors='replace')})"
    except Exception as e:
        return False, f"API handshake failed ({type(e).__name__}) — Gateway may be logged out"
    finally:
        s.close()


def check_finnhub():
    """Finnhub API key valid and endpoint responding."""
    import requests
    key = os.environ.get("FINNHUB_API_KEY")
    if not key:
        return False, "FINNHUB_API_KEY not set"
    try:
        r = requests.get("https://finnhub.io/api/v1/quote",
                         params={"symbol": "AAPL", "token": key}, timeout=10)
        if r.status_code in (401, 403):
            return False, f"auth failed (HTTP {r.status_code}) — key invalid/expired"
        r.raise_for_status()
        return (("c" in r.json()), "responding")
    except Exception as e:
        return False, f"request failed ({str(e)[:60]})"


def check_yahoo():
    """yfinance can fetch a quote."""
    try:
        import yfinance as yf
        h = yf.Ticker("AAPL").history(period="1d")
        return (not h.empty, "quote fetched" if not h.empty else "empty response")
    except Exception as e:
        return False, f"yfinance failed ({str(e)[:60]})"


def check_sec():
    """SEC EDGAR reachable (needs a descriptive User-Agent)."""
    import requests
    ua = os.environ.get("SEC_IDENTITY", "CompanyDataHub research@localhost")
    try:
        r = requests.get("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000320193&type=10-K&count=1",
                         headers={"User-Agent": ua}, timeout=10)
        return (r.status_code == 200, f"HTTP {r.status_code}")
    except Exception as e:
        return False, f"request failed ({str(e)[:60]})"


# --------------------------------------------------------------- freshness
def check_nav_freshness(db):
    """Age of the newest account-NAV point, against NAV_STALE_DAYS.

    Deliberately separate from freshness(): those sources are keyed on `fetched_at`,
    whereas NAV points are keyed on the trading date they represent (`period`). Also
    separate from check_ibkr(): a gateway that is down *right now* is tolerated, but
    a NAV series that has not advanced in a week is a real failure and DOES alert."""
    row = db.execute(
        """
        SELECT MAX(m.period) FROM metrics m
        JOIN instruments i ON i.id = m.company_id
        WHERE i.ticker = 'PORTFOLIO' AND m.metric = 'netliquidation'
        """
    ).fetchone()
    latest = row[0] if row else None
    if not latest:
        return False, "no NAV points recorded at all - has IB Gateway ever been up?"
    age = (datetime.now(timezone.utc).date() - date.fromisoformat(latest)).days
    if age > NAV_STALE_DAYS:
        return False, (f"stale: newest point {latest} ({age}d old, limit "
                       f"{NAV_STALE_DAYS}d) - IB Gateway has been down too long")
    return True, f"fresh: newest point {latest} ({age}d old)"


def freshness(db):
    rows = {
        "prices":       db.execute("SELECT MAX(fetched_at) FROM prices").fetchone()[0],
        "fundamentals": db.execute("SELECT MAX(fetched_at) FROM metrics").fetchone()[0],
        "filings":      db.execute("SELECT MAX(fetched_at) FROM filings").fetchone()[0],
        "news":         db.execute("SELECT MAX(fetched_at) FROM news").fetchone()[0],
    }
    out = {}
    for k, ts in rows.items():
        age = _age_days(ts)
        limit = FRESH_LIMIT[k]
        if age is None:
            out[k] = (False, "no data at all")
        elif age > limit:
            out[k] = (False, f"stale: {age:.1f}d old (limit {limit}d)")
        else:
            out[k] = (True, f"fresh: {age:.1f}d old")
    return out


def run_checks():
    """Return (all_ok, report_lines, failures)."""
    db = store.get_db()
    live = {
        "IBKR (prices)":     check_ibkr(),
        "Finnhub (news)":    check_finnhub(),
        "Yahoo (fundamentals)": check_yahoo(),
        "SEC (filings)":     check_sec(),
    }
    fresh = freshness(db)

    lines, failures = [], []
    lines.append("LIVE CONNECTIVITY")
    for name, (ok, msg) in live.items():
        lines.append(f"  [{'OK ' if ok else 'FAIL'}] {name:<22} {msg}")
        # IB Gateway is flaky and self-recovers on the next scheduled restart;
        # its failures are shown in the report but never trigger an email alert.
        if not ok and not name.startswith("IBKR"):
            failures.append(f"{name}: {msg}")

    nav_ok, nav_msg = check_nav_freshness(db)
    lines.append(f"  [{'OK ' if nav_ok else 'FAIL'}] {'account NAV':<22} {nav_msg}")
    # Unlike IBKR connectivity above, a prolonged NAV gap DOES alert - see
    # NAV_STALE_DAYS. One missed day is flakiness; a week is a broken pipeline.
    if not nav_ok:
        failures.append(f"account NAV: {nav_msg}")

    lines.append("\nDATA FRESHNESS")
    label = {"prices": "prices", "fundamentals": "fundamentals",
             "filings": "filings", "news": "news"}
    for k, (ok, msg) in fresh.items():
        lines.append(f"  [{'OK ' if ok else 'FAIL'}] {label[k]:<22} {msg}")
        if not ok:
            failures.append(f"{label[k]} freshness: {msg}")

    return (len(failures) == 0), lines, failures


# --------------------------------------------------------------- email
def send_email(subject, body):
    user = os.environ.get("SMTP_USER")
    pw = os.environ.get("SMTP_PASSWORD")
    to = os.environ.get("ALERT_EMAIL_TO", DEFAULT_ALERT_TO)
    sender = os.environ.get("ALERT_EMAIL_FROM", user)
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))

    if not (user and pw):
        print("\n⚠ Cannot send email: SMTP_USER / SMTP_PASSWORD not set in .env.")
        print("  Add a Gmail App Password (see header of this file) to enable alerts.")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    msg.set_content(body)
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=20) as s:
            s.login(user, pw)
            s.send_message(msg)
        print(f"\n✉ Alert emailed to {to}")
        return True
    except Exception as e:
        print(f"\n✗ Email send failed: {e}")
        return False


def main():
    ap = argparse.ArgumentParser(description="Data-source health check + email alert")
    ap.add_argument("--always-email", action="store_true", help="email even when all OK")
    ap.add_argument("--dry-run", action="store_true", help="never send; just print")
    args = ap.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    all_ok, lines, failures = run_checks()

    report = f"MarketHub — health check @ {stamp}\n\n" + "\n".join(lines)
    print(report)

    if args.dry_run:
        print("\n(dry-run: no email sent)")
        return 0 if all_ok else 1

    if not all_ok:
        subject = f"⚠ MarketHub ALERT: {len(failures)} source(s) down — {stamp}"
        body = (report + "\n\nFAILURES:\n" + "\n".join(f"  - {f}" for f in failures)
                + "\n\nCheck: IB Gateway logged in? API keys valid? network up?")
        send_email(subject, body)
        return 1
    elif args.always_email:
        send_email(f"✓ MarketHub OK — {stamp}", report)

    print("\n✓ All sources healthy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
