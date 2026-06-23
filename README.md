# Company Data Hub

Automated equity research data collection system tracking 154 companies across 19 industries.

## What This Collects

**News & Research:**
- Company press releases and official announcements
- Financial news from Bloomberg, Wall Street Journal, TechCrunch
- Industry analysis from BioPharma Dive, EE Times, SemiAnalysis
- Venture capital and startup funding news from Crunchbase, PitchBook
- Podcast episode descriptions from Morgan Stanley, Goldman Sachs, a16z, Acquired

**SEC Filings:**
- 10-K annual reports (full business overview, financials, risk factors)
- 10-Q quarterly reports (recent performance updates)
- 8-K material event filings (M&A, leadership changes, earnings releases)

## Data Storage

All data stored locally in SQLite database (`finance.db`):
- Full article text (not summaries)
- Complete SEC filing text
- Publication dates and sources
- Company and industry tags

## Data Sources

All sources are free and publicly available:

**Official Company RSS Feeds (20 companies):**
- Apple, Microsoft, Amazon, NVIDIA, Meta Platforms, Intel, Oracle, Netflix, AMD, Stripe, OpenAI, SpaceX, Databricks, PayPal, Lockheed Martin, Salesforce, IBM, Cisco, Coinbase

**Financial News:**
- Bloomberg Technology
- Wall Street Journal Markets & Technology
- TechCrunch

**Industry Research Publications:**
- BioPharma Dive (biotech/pharma news)
- FierceBiotech (drug development, R&D)
- EE Times (semiconductor industry)
- SemiWiki (chip design)
- SemiAnalysis (technical chip analysis)
- Crunchbase News (venture funding)
- PitchBook Blog (VC/PE insights)

**Financial Research Podcasts (episode descriptions):**
- Morgan Stanley "Thoughts on the Market"
- Goldman Sachs "Exchanges"
- JPMorgan Global Research
- a16z Show
- Acquired (Ben Gilbert & David Rosenthal)
- Invest Like the Best

**SEC EDGAR:**
- All public company filings via SEC's official API
- 10-K, 10-Q, 8-K forms with full text

## Industries Tracked

19 industries, 154 companies total:

- Semiconductors (10 companies)
- Artificial Intelligence (14 companies)
- Automotive (10 companies)
- Energy (10 companies)
- Aerospace (8 companies)
- Defense & Space (10 companies)
- Cloud & Software (11 companies)
- Financials & Banks (10 companies)
- Biotech & Pharma (10 companies)
- Cybersecurity (9 companies)
- Fintech & Payments (12 companies)
- Healthcare & Medical Devices (10 companies)
- Consumer & Retail (10 companies)
- Media & Streaming (8 companies)
- Crypto & Digital Assets (7 companies)
- AI Infrastructure & Data Centers (11 companies)
- Robotics & Automation (9 companies)
- Energy Storage (9 companies)
- Transportation & Logistics (9 companies)

See `industries.json` for complete company list.

## Web Dashboard

View collected data at **http://localhost:8000** (run `python dashboard.py` or `docker-compose up -d`)

**Features:**
- Browse by industry
- View companies, news articles, and SEC filings
- Click news titles to read full article text
- Click filings to see complete SEC documents
- Real-time statistics

## Setup & Usage

See setup guides:
- `DOCKER.md` - Docker setup (recommended for OrbStack users)
- `AUTOMATION.md` - Automated daily collection setup
- `PLAN.md` - Development roadmap
