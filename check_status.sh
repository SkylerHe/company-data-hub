#!/bin/bash
# Quick status check script - see what data was collected and when

cd "$(dirname "$0")"
source venv/bin/activate

echo "=================================================="
echo "  COMPANY DATA HUB - STATUS REPORT"
echo "=================================================="
echo ""

# Check if automation is running
echo "📅 AUTOMATION STATUS:"
if launchctl list | grep -q com.companydata.scraper; then
    echo "  ✓ Automated collection is ACTIVE"
    echo "  ⏰ Scheduled to run daily at 9:00 AM"
else
    echo "  ✗ Automated collection is NOT set up"
    echo "  Run: ./setup_automation.sh to enable"
fi
echo ""

# Last run time from logs
echo "🕐 LAST COLLECTION RUN:"
if [ -f scraper.log ]; then
    last_run=$(grep "Starting news collection" scraper.log | tail -1)
    if [ ! -z "$last_run" ]; then
        echo "  $last_run"
    else
        echo "  No runs logged yet"
    fi
else
    echo "  No log file found - hasn't run yet"
fi
echo ""

# Database statistics
echo "📊 DATABASE STATS:"
python store.py --stats 2>/dev/null | head -25
echo ""

# Recent activity
echo "📰 RECENT NEWS COLLECTED:"
sqlite3 finance.db "
SELECT
    strftime('%Y-%m-%d', fetched_at) as date,
    COUNT(*) as articles
FROM news
GROUP BY date
ORDER BY date DESC
LIMIT 7
" 2>/dev/null | awk '{print "  " $0}'
echo ""

echo "📄 RECENT SEC FILINGS COLLECTED:"
sqlite3 finance.db "
SELECT
    strftime('%Y-%m-%d', fetched_at) as date,
    type,
    COUNT(*) as count
FROM filings
GROUP BY date, type
ORDER BY date DESC, type
LIMIT 10
" 2>/dev/null | awk '{print "  " $0}'
echo ""

echo "🔍 TOP 5 COMPANIES BY DATA COLLECTED:"
sqlite3 finance.db "
SELECT
    c.name,
    COUNT(DISTINCT n.id) + COUNT(DISTINCT f.id) as total_items
FROM companies c
LEFT JOIN news n ON c.id = n.company_id
LEFT JOIN filings f ON c.id = f.company_id
GROUP BY c.id
ORDER BY total_items DESC
LIMIT 5
" 2>/dev/null | awk '{print "  " $0}'
echo ""

echo "=================================================="
echo "To view logs: tail -f scraper.log"
echo "To run now:   launchctl start com.companydata.scraper"
echo "=================================================="
