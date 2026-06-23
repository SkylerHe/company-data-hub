# company-data-hub

Daily news collection for 154 companies across 19 industries. Everything runs locally with SQLite.

## What This Does

Scrapes news, research, and podcasts about companies you track. Stores full article text in a local database.

## Quick Start

```bash
pip install -r requirements.txt

# Set up your SEC identity (required for filing scraper)
echo 'SEC_IDENTITY="YourName your.email@example.com"' > .env

# Initialize database and load companies
python store.py --init
python store.py --load industries.json

# Initial backfill (run once to get all filings since 2024)
python scrape_filings.py --since 2024-01-01

# Daily operations
python scrape.py                    # Collect news
python scrape_filings.py            # Collect new filings
python store.py --stats             # View results
```

## Data Sources (All Free)

**Official company feeds (20 companies):**
Apple, Microsoft, Amazon, NVIDIA, Meta, Intel, Oracle, Netflix, etc.

**News outlets:**
Bloomberg, Wall Street Journal, TechCrunch

**Industry research:**
BioPharma Dive, FierceBiotech, EE Times, SemiAnalysis, Crunchbase, PitchBook

**Podcasts (episode descriptions):**
Morgan Stanley, Goldman Sachs, JPMorgan, a16z, Acquired, Invest Like the Best

**SEC filings (for public companies):**
10-K (annual reports), 10-Q (quarterly reports), 8-K (material events)

## Data Collected

- **Full article text** (not summaries)
- **SEC filing full text** (10-K, 10-Q, 8-K)
- **Podcast episode descriptions**
- **Publication dates and sources**
- **Company and industry tags**

Stored in SQLite database (`finance.db`)

## Files

- `scrape.py` - Daily news scraper
- `scrape_filings.py` - SEC filing scraper (requires SEC_IDENTITY env var)
- `store.py` - Database operations
- `sources.yaml` - RSS feed configuration
- `industries.json` - 154 companies × 19 industries
- `finance.db` - SQLite database (created on first run)

## Automated Collection

Set up daily automated collection that runs even when you're not actively using your computer:

```bash
# One-command setup (runs daily at 9 AM automatically)
./setup_automation.sh
```

This sets up macOS launchd to run data collection every day at 9 AM. Works even when:
- Terminal is closed
- You're not logged in
- Computer wakes from sleep

**Alternative options:** See `AUTOMATION.md` for cron setup, GitHub Actions, or cloud deployment.

## View Your Data

### Web Dashboard (Recommended)

Visual, easy-to-use interface in your browser:

```bash
python dashboard.py
```

Then open: **http://localhost:8000**

Features:
- 📊 Live statistics (companies, industries, news, filings)
- 🏭 Browse by industry
- 🏢 View companies in each industry
- 📰 Latest news articles by industry
- 📄 Latest SEC filings by industry
- Clean, modern UI

### Command Line Tools

```bash
# Quick status check
./check_status.sh

# Interactive terminal browser
./view_data.sh

# Raw database stats
python store.py --stats

# Watch live collection logs
tail -f scraper.log
```

## Next Steps

See `PLAN.md` for full roadmap to build equity research platform.
