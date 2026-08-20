#!/bin/bash
# run_daily.sh - one scheduled pass: extract everything due, then health-check + alert.
# Invoked by the launchd agent (see setup_automation.sh). Safe to run by hand too.

cd "$(dirname "$0")" || exit 1
PY="./venv/bin/python"
LOG="scraper.log"

# --- hard wall-clock cap per step -------------------------------------------
# launchd will NOT start a new instance while the previous one is still alive, so
# a single hung child silently kills every future run. That is exactly what
# happened 2026-08-13: scrape_ibkr.py hit IB Gateway in its degraded state (port
# open, data requests never answered), hung with no timeout, and run_daily.sh
# stayed alive for 7 days -- no daily run in between, prices/filings/news all went
# stale, and nothing alerted.
#
# macOS ships no coreutils `timeout`, so this is a bash-native watchdog. Kills the
# whole process tree, since the hang is usually in a python grandchild.
STEP_TIMEOUT_UPDATE=3600   # update.py: prices+fundamentals+filings+news, ~180 names
STEP_TIMEOUT_SHORT=300     # NAV point and health check

_kill_tree() {
  local p=$1 c
  for c in $(pgrep -P "$p" 2>/dev/null); do _kill_tree "$c"; done
  kill -9 "$p" 2>/dev/null
}

run_step() {
  local limit=$1; shift
  "$@" &
  local cmd_pid=$!
  ( sleep "$limit"; _kill_tree "$cmd_pid" ) &
  local watch_pid=$!
  wait "$cmd_pid" 2>/dev/null
  local rc=$?
  _kill_tree "$watch_pid" 2>/dev/null
  wait "$watch_pid" 2>/dev/null
  if [ $rc -ge 128 ]; then
    echo "!! step exceeded ${limit}s wall clock and was killed: $*"
    return 124
  fi
  return $rc
}

{
  echo "======================================================================"
  echo "$(date '+%Y-%m-%d %H:%M:%S')  daily run START"
  echo "======================================================================"

  # 1. Smart extraction: prices (daily), fundamentals (14d), filings (7d), news (2d).
  echo "--- update.py ---"
  run_step "$STEP_TIMEOUT_UPDATE" "$PY" update.py
  UPDATE_RC=$?
  echo "update.py exit code: $UPDATE_RC"

  # 1b. Record account NAV (netliquidation) so the NAV-vs-index curve accumulates
  #     one point per day. Needs IB Gateway; a down gateway just skips today's point
  #     (non-fatal — like the price scraper, IBKR flakiness self-recovers).
  echo "--- scrape_ibkr_account.py --account (daily NAV point) ---"
  run_step "$STEP_TIMEOUT_SHORT" "$PY" scrape_ibkr_account.py --account
  echo "account NAV exit code: $?"

  # 2. Full status check. Emails skyleryh6km@gmail.com if any source is down/stale.
  echo "--- health_check.py ---"
  run_step "$STEP_TIMEOUT_SHORT" "$PY" health_check.py
  HC_RC=$?
  echo "health_check.py exit code: $HC_RC  (0 = all healthy, 1 = alert sent)"

  echo "$(date '+%Y-%m-%d %H:%M:%S')  daily run DONE"
  echo ""
} >> "$LOG" 2>&1
