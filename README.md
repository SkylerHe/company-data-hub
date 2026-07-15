# MarketHub
**Financial data collection for CFA Level 1 study + trading practice**

## 🚀 Quick Start

### 1. View Your Data
```bash
python dashboard.py
# Open: http://localhost:8000
```

### 2. Update Data
```bash
# Smart update (checks what needs updating)
python update.py

# Or update specific data
python update.py --prices-only      # Just prices
python update.py --fundamentals     # Just fundamentals
python update.py --force-all        # Force everything
```

## 📊 What You Have

- **155 companies** across 8 GICS sectors
- **3,163 SEC filings** (10-K, 10-Q, 8-K)
- **247,321+ price data points** (up to 5 years from IBKR)
- **3,695+ fundamental metrics** (Yahoo Finance)
- **Financial news** (optional, Finnhub API)

## 📚 Data Sources

| Source | Data | Update Frequency |
|--------|------|------------------|
| Yahoo Finance | P/E, ROE, margins, etc. | Bi-weekly |
| IBKR | Daily OHLCV prices | Daily |
| SEC EDGAR | 10-K, 10-Q, 8-K filings | Weekly |
| Finnhub | Financial news | 3x per week |

## 🔐 Setup

### IB Gateway (for prices)
```bash
# 1. Open IB Gateway (port 4001)
# 2. Enable API in settings
# 3. Run price updates
python scrape_ibkr.py --prices-only --years 5  # First time: 5 years
python update.py --prices-only                 # Daily: 1 year refresh
```

### Finnhub News (optional)
```bash
# 1. Get free API key: https://finnhub.io/register
# 2. Set environment variable
export FINNHUB_API_KEY='your_key_here'

# 3. Collect news
python scrape_news.py --days 30
```

### SEC Filings
```bash
export SEC_IDENTITY="YourName email@example.com"
```

## 📖 For CFA Study

**Your data covers these Level 1 topics:**
- ✅ Financial Reporting & Analysis (SEC filings)
- ✅ Equity Investments (all valuation ratios)
- ✅ Corporate Finance (fundamentals, ratios)
- ✅ Portfolio Management (price history for backtesting)

**Practice exercises:**
```bash
# 1. Compare two companies
sqlite3 finance.db "
SELECT c.name, m.metric, m.value
FROM metrics m
JOIN companies c ON m.company_id = c.id
WHERE m.metric = 'pe_ratio'
  AND c.name IN ('NVIDIA', 'AMD')
  AND m.source = 'Yahoo'
"

# 2. Find undervalued stocks
sqlite3 finance.db "
SELECT c.name,
       MAX(CASE WHEN m.metric = 'pe_ratio' THEN m.value END) as pe,
       MAX(CASE WHEN m.metric = 'roe' THEN m.value END) as roe
FROM metrics m
JOIN companies c ON m.company_id = c.id
WHERE m.source = 'Yahoo'
GROUP BY c.name
HAVING pe < 20 AND roe > 15
ORDER BY roe DESC
"
```

## 📁 Project Structure

```
company-data-hub/
├── update.py              # ⭐ Smart update (run this!)
├── dashboard.py           # Web UI
├── scrape_yahoo.py        # Fundamentals + earnings dates
├── scrape_ibkr.py         # Historical prices (1-5 years)
├── scrape_filings.py      # SEC filings
├── scrape_news.py         # Financial news
├── finance.db             # Your database
├── SUMMARY.md             # Detailed documentation
└── industries.json        # Company list
```

## 🔄 Automation

Add to crontab for automatic updates:
```bash
# Run update check daily at 6 PM
0 18 * * * cd /path/to/company-data-hub && python update.py

# The script automatically:
# - Updates prices daily
# - Updates fundamentals bi-weekly
# - Updates filings weekly
# - Updates news 3x per week
```

## 💡 Tips

**Learning fundamentals:**
1. Pick 2 companies in same sector
2. Compare P/E, ROE, debt/equity
3. Read their latest 10-K
4. Practice calculating ratios manually

**Paper trading:**
1. Use IBKR paper account ($1M fake money)
2. Analyze fundamentals → pick stocks
3. Practice limit orders, stop losses
4. Track results for 2-4 weeks

**CFA prep:**
- Use your data to practice every formula
- Compare your calculations to Yahoo Finance
- Read SEC filings for real-world examples

See `SUMMARY.md` for complete documentation.
