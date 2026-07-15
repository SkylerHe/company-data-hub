# MarketHub - Resource Summary
**Updated for CFA Level 1 + Trading Practice**

## 📊 Database Contents

| Data Type | Count | Description |
|-----------|-------|-------------|
| **Companies** | 155 | Tracked across 8 GICS sectors |
| **SEC Filings** | 3,163 | 10-K, 10-Q, 8-K (2024-present) |
| **Historical Prices** | 247,321+ | Daily OHLCV from IBKR (up to 5 years) |
| **Fundamentals** | 3,695+ | Financial ratios + earnings dates (Yahoo) |
| **News** | 0 (new) | Finnhub financial news (requires free API key) |

## 🏢 Sector Coverage (GICS Standard)

| Sector | Companies |
|--------|-----------|
| Technology | 43 |
| Industrials | 31 |
| Financials | 25 |
| Healthcare | 19 |
| Energy | 17 |
| Consumer Discretionary | 15 |
| Communication Services | 8 |
| Consumer Staples | 5 |

## 📈 Available Metrics

### Valuation Ratios
- P/E (trailing & forward)
- P/B, P/S
- EV/EBITDA
- PEG ratio

### Profitability
- Gross margin
- Operating margin
- Net profit margin
- ROE, ROA

### Growth
- Revenue growth (YoY)
- Earnings growth (YoY, QoQ)

### Financial Health
- Debt/Equity ratio
- Current ratio
- Quick ratio

### Fundamentals
- Revenue, Cash, Total Debt
- Market Cap
- Shares Outstanding
- Free Cash Flow
- Beta, Dividend Yield

## 🔄 Update Commands

```bash
# ⭐ SMART UPDATE (Recommended)
python update.py
# Automatically checks what needs updating:
# - Prices: Daily
# - Fundamentals: Bi-weekly (every 14 days)
# - Filings: Weekly (every 7 days)
# - News: 3x per week (every 2 days)

# Manual updates:
python update.py --prices-only      # Just update prices
python update.py --fundamentals     # Just update fundamentals
python update.py --force-all        # Force update everything

# First-time setup:
python scrape_ibkr.py --prices-only --years 5  # Get 5 years of history
```

## 📁 Active Scripts

| Script | Purpose |
|--------|---------|
| `update.py` | **⭐ Smart update - checks what needs updating** |
| `dashboard.py` | Web UI to view all data |
| **Individual Scrapers:** | |
| `scrape_yahoo.py` | Fundamentals + earnings dates (bi-weekly) |
| `scrape_ibkr.py` | Historical prices 1-5 years (daily) |
| `scrape_filings.py` | SEC filings (weekly) |
| `scrape_news.py` | Financial news (3x/week, optional) |
| `scrape_ibkr_account.py` | Your IBKR portfolio/trades |
| **Configuration:** | |
| `store.py` | Database schema & operations |
| `industries.json` | Company list & sectors |

## 🌐 View Your Data

```bash
python dashboard.py
# Then open: http://localhost:8000
```

## 🗄️ Database Schema

**Tables:**
- `companies` - Company details & tickers
- `industries` - GICS sectors
- `company_industries` - Company-sector mapping
- `news` - Full-text news articles
- `filings` - SEC filing content
- `metrics` - Time-series financial data (IBKR prices + Yahoo fundamentals)

## 🔌 Data Sources

1. **News**: RSS feeds → trafilatura (full article text)
2. **SEC Filings**: EDGAR API (official SEC data)
3. **Prices**: Interactive Brokers API (requires IB Gateway)
4. **Fundamentals**: Yahoo Finance API (free, no key needed)

## 📝 Configuration Files

- `industries.json` - Company list & sector assignments
- `requirements.txt` - Python dependencies
- `docker-compose.yml` - Automated collection setup
- `finance.db` - SQLite database (all data)

## 💾 Database File

**Location**: `finance.db`
**Size**: ~50-100MB
**Format**: SQLite 3

**Query examples:**
```bash
# View all companies in Technology sector
sqlite3 finance.db "
SELECT c.name, c.ticker
FROM companies c
JOIN company_industries ci ON c.id = ci.company_id
JOIN industries i ON ci.industry_id = i.id
WHERE i.name = 'Technology'
ORDER BY c.name
"

# Get latest Yahoo fundamentals for NVIDIA
sqlite3 finance.db "
SELECT metric, value, unit
FROM metrics m
JOIN companies c ON m.company_id = c.id
WHERE c.name = 'NVIDIA' AND m.source = 'Yahoo'
ORDER BY metric
"
```

## 🚀 Automation

**Recommended: Run once daily and let the script decide what needs updating**

```bash
# Add to crontab (run daily at 6 PM after market close)
0 18 * * * cd /path/to/company-data-hub && python update.py

# The script automatically:
# - Updates prices daily (if IB Gateway running)
# - Updates fundamentals every 14 days
# - Updates filings every 7 days
# - Updates news every 2 days (if API key set)
```

**Or schedule specific times:**
```bash
# Prices: Daily at 6 PM (after market close)
0 18 * * * cd /path/to/company-data-hub && python update.py --prices-only

# Fundamentals: Every other Monday at 7 AM
0 7 */14 * 1 cd /path/to/company-data-hub && python scrape_yahoo.py

# Filings: Every Monday at 7 AM
0 7 * * 1 cd /path/to/company-data-hub && python scrape_filings.py
```

## 📊 What You Can Analyze

1. **Valuation screening**: Find undervalued stocks by P/E, P/B, PEG
2. **Growth analysis**: Track revenue/earnings growth trends
3. **Sector comparison**: Compare metrics across GICS sectors
4. **News monitoring**: Full-text search across 861 articles
5. **Filing analysis**: Read complete 10-K/10-Q content
6. **Price trends**: 365 days of OHLCV data for charts
7. **Financial health**: Debt ratios, liquidity metrics

## 🔐 Required Setup

### 1. IB Gateway (for price updates)
- Paper trading account: port 4001
- Enable API in account settings
- Run IB Gateway before using `scrape_ibkr.py`

### 2. SEC EDGAR (for filings)
```bash
export SEC_IDENTITY="YourName email@example.com"
```

### 3. Finnhub API (for news) - **NEW!**
Get free API key: https://finnhub.io/register
```bash
export FINNHUB_API_KEY='your_key_here'
```
Free tier: 60 requests/minute

### 4. No API keys needed
- Yahoo Finance ✓
- SEC filings ✓ (just email)

---

## 🚀 Quick Start - New Features

### Get 5 Years of Historical Data
```bash
# Start IB Gateway first, then:
python scrape_ibkr.py --prices-only --years 5
```

### Enable News Collection
```bash
# 1. Get API key from https://finnhub.io/register
# 2. Export it
export FINNHUB_API_KEY='your_key_here'

# 3. Collect news
python scrape_news.py --days 30
```

### Daily Updates (Run This Every Day)
```bash
# Option 1: All-in-one (easiest)
python update_daily.py

# Option 2: Without IBKR (if Gateway not running)
python update_daily.py --skip-ibkr

# Option 3: Just fundamentals & filings (no news)
python update_daily.py --skip-news --skip-ibkr
```
