#!/bin/bash
# Quick automation setup for company-data-hub

echo "Setting up automated daily data collection..."
echo ""

# Create launch agent directory
mkdir -p ~/Library/LaunchAgents

# Create the plist file
cat > ~/Library/LaunchAgents/com.companydata.scraper.plist << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.companydata.scraper</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/skylerhe/company-data-hub/run_daily.sh</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/skylerhe/company-data-hub/scraper.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/skylerhe/company-data-hub/scraper_error.log</string>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
PLIST

# Load the launch agent
launchctl load ~/Library/LaunchAgents/com.companydata.scraper.plist

echo "✓ Automation configured!"
echo ""
echo "Your data collection will now run automatically every day at 9:00 AM"
echo ""
echo "Useful commands:"
echo "  - Check status: launchctl list | grep companydata"
echo "  - View logs: tail -f ~/company-data-hub/scraper.log"
echo "  - Run now: launchctl start com.companydata.scraper"
echo "  - Stop: launchctl unload ~/Library/LaunchAgents/com.companydata.scraper.plist"
echo ""
