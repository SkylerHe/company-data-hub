# Automated Data Collection Setup

This guide shows you how to set up automatic daily collection that runs even when you're not using your computer.

## Option 1: macOS launchd (Recommended for Mac)

launchd is the macOS native scheduler - more reliable than cron, works even when Terminal is closed.

### Setup Steps:

1. **Create the launch agent file:**

```bash
mkdir -p ~/Library/LaunchAgents

cat > ~/Library/LaunchAgents/com.companydata.scraper.plist << 'EOF'
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
EOF
```

2. **Load the launch agent:**

```bash
launchctl load ~/Library/LaunchAgents/com.companydata.scraper.plist
```

3. **Verify it's loaded:**

```bash
launchctl list | grep companydata
```

You should see `com.companydata.scraper` in the output.

### What This Does:

- Runs `run_daily.sh` every day at 9:00 AM
- Works even when you're not logged in (as long as Mac is on)
- Logs output to `scraper.log` and `scraper_error.log`

### Management Commands:

```bash
# Check status
launchctl list | grep companydata

# Stop the scheduler
launchctl unload ~/Library/LaunchAgents/com.companydata.scraper.plist

# Restart the scheduler
launchctl unload ~/Library/LaunchAgents/com.companydata.scraper.plist
launchctl load ~/Library/LaunchAgents/com.companydata.scraper.plist

# Run it manually right now (for testing)
launchctl start com.companydata.scraper

# View logs
tail -f ~/company-data-hub/scraper.log
```

### Change Schedule:

Edit `~/Library/LaunchAgents/com.companydata.scraper.plist`:

**Run every 6 hours:**
```xml
<key>StartInterval</key>
<integer>21600</integer>  <!-- 6 hours in seconds -->
```

**Run at specific times (e.g., 9 AM and 6 PM):**
```xml
<key>StartCalendarInterval</key>
<array>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <dict>
        <key>Hour</key>
        <integer>18</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
</array>
```

After editing, reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.companydata.scraper.plist
launchctl load ~/Library/LaunchAgents/com.companydata.scraper.plist
```

---

## Option 2: Cron (Alternative)

If you prefer traditional cron:

1. **Open crontab editor:**

```bash
crontab -e
```

2. **Add this line to run daily at 9 AM:**

```cron
0 9 * * * /Users/skylerhe/company-data-hub/run_daily.sh
```

3. **Save and exit** (press `Esc`, type `:wq`, press Enter if using vim)

### Cron Schedule Examples:

```cron
# Every day at 9 AM
0 9 * * * /Users/skylerhe/company-data-hub/run_daily.sh

# Every 6 hours
0 */6 * * * /Users/skylerhe/company-data-hub/run_daily.sh

# Weekdays at 6 AM
0 6 * * 1-5 /Users/skylerhe/company-data-hub/run_daily.sh

# First day of every month at midnight
0 0 1 * * /Users/skylerhe/company-data-hub/run_daily.sh
```

**View your cron jobs:**
```bash
crontab -l
```

**Remove all cron jobs:**
```bash
crontab -r
```

---

## Option 3: Cloud/Server Deployment

For truly automated collection that doesn't require your Mac to be on:

### GitHub Actions (Free, runs in the cloud)

Already set up in `.github/workflows/scrape.yml`:
- Runs daily at 6 AM UTC
- Collects news and filings
- Stores data in GitHub releases as artifacts

**To enable:**
1. Push your repo to GitHub
2. Go to Settings → Secrets → Add `SEC_IDENTITY` secret
3. Enable GitHub Actions in repo settings

### Other Options:
- **AWS Lambda + EventBridge**: Free tier, schedule Python functions
- **Google Cloud Run + Cloud Scheduler**: $0.40/month for daily runs
- **DigitalOcean Droplet**: $6/month for a small VPS
- **Railway.app**: Free tier with cron jobs

---

## Verify It's Working

After setting up automation, check that it's collecting data:

```bash
# View recent logs
tail -50 ~/company-data-hub/scraper.log

# Check database stats
cd ~/company-data-hub
source venv/bin/activate
python store.py --stats

# See when last data was collected
sqlite3 finance.db "SELECT MAX(fetched_at) FROM news;"
sqlite3 finance.db "SELECT MAX(fetched_at) FROM filings;"
```

---

## Troubleshooting

**Script doesn't run:**
- Check logs: `tail -f ~/company-data-hub/scraper_error.log`
- Verify file permissions: `ls -la ~/company-data-hub/run_daily.sh`
- Make sure paths are absolute (not `~/`, use `/Users/skylerhe/`)

**No new data collected:**
- Companies don't release news/filings every day
- Check watermarks: `sqlite3 finance.db "SELECT name, last_fetched FROM companies WHERE last_fetched IS NOT NULL LIMIT 10;"`
- Run manually to test: `./run_daily.sh`

**Mac sleeps and misses runs:**
- launchd will run on next wake if `RunAtLoad` is true
- Or use `caffeinate` to prevent sleep during runs
- Or deploy to a cloud service

---

## Recommended Schedule

**For comprehensive coverage:**
- **News scraper**: Daily (news comes out every day)
- **SEC filings**: Weekly or monthly (filings are quarterly, no need for daily)

**Modify `run_daily.sh` for weekly filings:**
```bash
# Run filings only on Mondays
if [ $(date +%u) -eq 1 ]; then
    python scrape_filings.py >> scraper.log 2>&1
fi
```

Or create separate schedules:
- News: Daily at 9 AM
- Filings: Every Monday at 10 AM
