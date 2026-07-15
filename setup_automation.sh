#!/bin/bash
# setup_automation.sh - install/refresh the launchd agent that runs run_daily.sh.
# Default schedule: every day at 18:00 local (after US market close). Change the
# Hour/Minute below and re-run to adjust.

set -e
REPO="$(cd "$(dirname "$0")" && pwd)"
LABEL="com.companydata.datahub"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
HOUR=18
MINUTE=0

mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$REPO/run_daily.sh</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>$HOUR</integer>
        <key>Minute</key><integer>$MINUTE</integer>
    </dict>

    <key>WorkingDirectory</key>
    <string>$REPO</string>

    <key>StandardOutPath</key>
    <string>$REPO/launchd.out.log</string>
    <key>StandardErrorPath</key>
    <string>$REPO/launchd.err.log</string>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
PLISTEOF

# reload
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "Installed launchd agent: $LABEL"
echo "  runs: $REPO/run_daily.sh  daily at $(printf '%02d:%02d' $HOUR $MINUTE) local"
echo "  plist: $PLIST"
echo ""
echo "Manage it:"
echo "  launchctl list | grep companydata          # is it registered?"
echo "  launchctl start $LABEL                      # run once right now"
echo "  launchctl unload $PLIST                     # disable"
