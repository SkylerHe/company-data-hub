#!/bin/bash
# Daily automated data collection script
# Run this via cron to collect news and SEC filings automatically

cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Run news scraper
echo "$(date): Starting news collection..." >> scraper.log
python scrape.py >> scraper.log 2>&1

# Run SEC filing scraper (will only collect new filings)
echo "$(date): Starting SEC filing collection..." >> scraper.log
python scrape_filings.py >> scraper.log 2>&1

echo "$(date): Collection complete" >> scraper.log
echo "---" >> scraper.log
