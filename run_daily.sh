#!/bin/bash
# run_daily.sh - one scheduled pass: extract everything due, then health-check + alert.
# Invoked by the launchd agent (see setup_automation.sh). Safe to run by hand too.

cd "$(dirname "$0")" || exit 1
PY="./venv/bin/python"
LOG="scraper.log"

{
  echo "======================================================================"
  echo "$(date '+%Y-%m-%d %H:%M:%S')  daily run START"
  echo "======================================================================"

  # 1. Smart extraction: prices (daily), fundamentals (14d), filings (7d), news (2d).
  echo "--- update.py ---"
  "$PY" update.py
  UPDATE_RC=$?
  echo "update.py exit code: $UPDATE_RC"

  # 1b. Record account NAV (netliquidation) so the NAV-vs-index curve accumulates
  #     one point per day. Needs IB Gateway; a down gateway just skips today's point
  #     (non-fatal — like the price scraper, IBKR flakiness self-recovers).
  echo "--- scrape_ibkr_account.py --account (daily NAV point) ---"
  "$PY" scrape_ibkr_account.py --account
  echo "account NAV exit code: $?"

  # 2. Full status check. Emails skyleryh6km@gmail.com if any source is down/stale.
  echo "--- health_check.py ---"
  "$PY" health_check.py
  HC_RC=$?
  echo "health_check.py exit code: $HC_RC  (0 = all healthy, 1 = alert sent)"

  echo "$(date '+%Y-%m-%d %H:%M:%S')  daily run DONE"
  echo ""
} >> "$LOG" 2>&1
