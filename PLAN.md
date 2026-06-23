# Equity Research Platform - Development Plan

This is your roadmap to become an equity research expert with your own data collection and analysis system.

## Goal

Build a personal equity research system that:
1. Collects comprehensive data on companies you track
2. Helps you understand industries, trends, and competitive positioning
3. Enables you to make informed investment decisions
4. Costs nothing (or very little) to run

## What You're Building Toward

**Input:** Companies you want to track (currently 154 across 19 industries)

**Output:** Ability to ask questions like:
- "What's NVIDIA's competitive position in AI chips?"
- "Which biotech companies have FDA approvals coming up?"
- "How is Tesla's energy storage business performing?"
- "What are the latest funding rounds in fintech?"

**Your advantage:** Real-time knowledge from company sources, not just Wikipedia or outdated data.

---

## Current Status: Phase 2 Complete ✅

**What you have now:**

✅ **News Collection (Phase 1)**
- 154 companies across 19 industries
- Daily scraping from official sources (Apple, Microsoft, NVIDIA, etc.)
- Financial news outlets (Bloomberg, WSJ, TechCrunch)
- Industry research (BioPharma Dive, EE Times, SemiAnalysis)
- Podcast summaries (Morgan Stanley, Goldman Sachs, Acquired)
- VC/startup news (Crunchbase, PitchBook)
- Full article text stored locally in SQLite

**What this gives you:**
- Industry trends and competitive moves
- Product launches and strategy shifts
- Market sentiment and analyst opinions
- Private company funding and valuations

✅ **SEC Filings (Phase 2)**
- 10-K (annual reports) - Full business overview, risk factors, financial statements
- 10-Q (quarterly reports) - Recent performance updates
- 8-K (material events) - M&A, leadership changes, major contracts
- Full filing text extracted and stored locally
- Built with edgartools library (free SEC EDGAR access)
- Currently collecting filings since 2024 for all public companies

**What this gives you:**
- Official company disclosures - the most reliable source for understanding a business
- Historical financial data and trends
- Risk factors and management discussion
- Material event notifications

---

## Phase 3: Financial Metrics (Next)

**Goal:** Track key financial numbers over time.

**What you'll get:**
- Revenue, profit, cash flow (quarterly and annual)
- Growth rates
- Margins
- Key ratios (P/E, debt-to-equity, etc.)

**How to build it:**
1. **Option A (Free):** Parse from 10-K/10-Q filings with LLM
2. **Option B (Easier):** Use free APIs like Alpha Vantage or Financial Modeling Prep (limited free tier)
3. Store in `metrics` table: `(company, metric, period, value, unit)`

**Value:** Track performance trends, compare companies, identify outliers.

**Time estimate:** 3-5 days

---

## Phase 4: Earnings Call Transcripts

**Goal:** Get management commentary and Q&A from quarterly earnings.

**What you'll get:**
- Management guidance and outlook
- Analyst questions and answers
- Strategic priorities
- Competitive positioning

**How to build it:**
1. **Option A (Free):** Scrape from Seeking Alpha or The Motley Fool
2. **Option B (Paid):** Use AlphaSense or similar ($$$)
3. Store full transcripts in `filings` table

**Value:** Hear directly from management, understand strategy, catch forward-looking insights.

**Time estimate:** 2-3 days

---

## Phase 5: Query & Analysis Layer

**Goal:** Ask questions and get answers from your data.

**Two paths:**

### Path A: Simple (Recommended to Start)

Build `ask.py`:
```bash
python ask.py "What's the latest on NVIDIA?"
```

**How it works:**
1. Load relevant data from SQLite
2. Send to LLM (local Ollama or cheap API)
3. Get answer with sources

**Cost:** Free with local model, or ~$0.01/query with API

### Path B: Advanced (Later)

Build MCP server for Claude Desktop integration:
- Query database from Claude chat interface
- Generate summaries on demand
- Create custom reports

**When to build:** After you're comfortable with simple queries

---

## Phase 6: Smart Summaries (Efficiency Multiplier)

**Goal:** Don't re-read everything every time you ask a question.

**What you'll build:**
- Daily summary generation per company (AI-generated dossier)
- Store in `companies.summary` field
- Update only when new data arrives

**How it works:**
1. New articles come in for NVIDIA
2. Run LLM over new content: "Summarize key developments"
3. Append to company summary (or regenerate monthly)
4. When you ask "What's up with NVIDIA?" → read summary, not 1000 articles

**Value:** Queries become instant and cheap. Read 154 summaries instead of 10,000 articles.

**Time estimate:** 2-3 days

---

## Phase 7: Podcast Transcription (Optional)

**Goal:** Get full text from podcast episodes, not just descriptions.

**Current state:** You have episode descriptions (200-500 words)

**Future upgrade:**
- Use OpenAI Whisper API ($0.36/hour of audio)
- Transcribe key podcasts automatically
- Store full transcripts

**Cost:** ~$15/month for 10 episodes/week

**When to build:** When descriptions aren't enough

---

## Phase 8: Market Data (Advanced)

**Goal:** Add real-time stock prices, volume, options data.

**Options:**
1. **Free:** Alpha Vantage, Yahoo Finance (delayed)
2. **Paid:** Interactive Brokers, Bloomberg Terminal
3. **Store in:** `prices` table with timestamps

**Note:** This requires always-on data collection (not just daily scraping)

**When to build:** After phases 2-5 are done

---

## Learning Path: Becoming an Equity Research Expert

**What equity researchers do:**
1. **Understand the business** - Read 10-Ks, understand products/services
2. **Analyze financials** - Revenue growth, margins, cash flow trends
3. **Track industry** - Competitive positioning, market size, trends
4. **Read management commentary** - Earnings calls, investor presentations
5. **Build models** - Forecast future performance
6. **Form opinions** - Buy/sell/hold recommendations

**Your system supports steps 1-4 above.** The tools you're building help you:
- Stay current (daily news)
- Go deep (SEC filings)
- Understand context (industry research)
- Hear from management (transcripts)

**What you still need to learn:**
- Financial modeling (Excel/Python)
- Valuation methods (DCF, comparable company analysis)
- Accounting basics (balance sheet, income statement, cash flow)

**Resources:**
- Coursera: Financial Markets (Yale, free)
- Damodaran on Valuation (NYU Stern, YouTube)
- SEC EDGAR tutorial (sec.gov)
- Practice: Pick 2-3 companies and follow them for 6 months

---

## Development Priorities

**Now (Phase 2):**
1. Build SEC filing scraper
2. Test on 5-10 companies
3. Verify full text is stored

**Next (Phase 3):**
1. Parse or fetch financial metrics
2. Build simple trending (revenue last 4 quarters)

**Then (Phase 5):**
1. Build `ask.py` query tool
2. Test with local model (free)

**Finally (Phase 6):**
1. Add summary generation
2. Set up daily refresh

---

## Success Metrics

**Phase 2 success:**
- All public companies have last 4 10-Qs and last 10-K stored
- Can view full filing text with `python store.py --show <url>`

**Phase 3 success:**
- Can see revenue trend for any company
- Can compare metrics across companies in same industry

**Phase 5 success:**
- Ask "What happened to NVIDIA this quarter?" and get coherent answer
- Answers include citations (article titles, filing dates)

**Overall success:**
- You confidently discuss companies you track
- You catch major developments within 24 hours
- You understand industry trends before mainstream news
- You make better investment decisions with data backing

---

## Cost Estimate

**Current (Phase 1):** $0/month
- All RSS feeds are free
- SQLite is free
- Storage: <1GB for years of data

**Phase 2-4:** $0/month
- SEC filings are free
- Basic financial data has free APIs

**Phase 5-6:** $0-5/month
- Free with local LLM (Ollama)
- Or ~$5/month with Claude/GPT if you query daily

**Phase 7 (optional):** ~$15/month
- Podcast transcription with Whisper

**Phase 8 (optional):** Varies
- Free delayed data available
- Real-time requires paid subscriptions

---

## Files Overview

```
store.py            - Database operations (core system)
scrape.py           - News collection (phase 1 ✅)
sources.yaml        - Feed configuration
industries.json     - Company/industry mappings
finance.db          - Your data (grows over time)

# To build:
scrape_filings.py   - SEC filing collection (phase 2)
scrape_metrics.py   - Financial metrics (phase 3)
scrape_transcripts.py - Earnings calls (phase 4)
ask.py              - Query interface (phase 5)
summarize.py        - Daily summary generation (phase 6)
```

---

## Next Steps

**Immediate (this week):**
1. Run daily scraper to build up news database
2. Review collected articles to verify quality
3. Start reading 10-Ks for 2-3 companies you're interested in

**This month:**
1. Build SEC filing scraper (phase 2)
2. Collect last year of filings for all public companies
3. Read through 2-3 full 10-Ks to understand structure

**Next month:**
1. Add financial metrics tracking (phase 3)
2. Build simple query tool (phase 5)
3. Start using the system daily

**Long-term (3-6 months):**
1. Build up domain knowledge in 2-3 industries
2. Track 10-20 companies closely
3. Form your first investment theses backed by data

---

## Remember

**You're building a research edge, not a trading bot.**

The goal isn't to predict stock prices. The goal is to:
- Understand businesses deeply
- Stay informed on your companies
- Make better decisions with better information
- Learn equity research skills that compound over time

Start simple. Add complexity only when needed. Focus on using what you build.
