# company-data-hub

Personal **financial-data platform + analysis toolkit** for CFA Level 1 study
and IBKR trading practice: collect market data into a local SQLite DB, then
read, value, and compare companies.

> **Full documentation** — architecture, file layout, how to run, the data
> model, and conventions — lives in **[CLAUDE.md](CLAUDE.md)**.

## Quick start
```bash
source venv/bin/activate

# Analysis (read-only; company name or ticker)
python analyze.py   --company MSFT              # fundamental health
python valuation.py --company MSFT              # intrinsic value + verdict
python report.py    --company MSFT              # → editable Excel model
python industry.py  --industry Semiconductors   # peer comparison

# Data
python update.py                    # smart refresh (prices/fundamentals/filings/news)
python health_check.py --dry-run    # status of every source
```

Secrets (SEC identity, SMTP, API keys) go in `.env` (gitignored). Run scripts
from the repo root — `finance.db` is resolved relative to the working directory.
