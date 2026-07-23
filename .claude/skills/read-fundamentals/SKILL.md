---
name: read-fundamentals
description: >-
  Read a single company's financial health from finance.db — is it profitable,
  is profitability improving or eroding, is the balance sheet sound, and are the
  earnings cash-backed (quality of earnings)? Produces a multi-year fundamental
  analysis with plain-English teaching notes (this is also the user's tool for
  LEARNING to read financial statements). Trigger on requests like "is MSFT
  healthy?", "read Nvidia's fundamentals", "how profitable is Costco?", "do an
  FSA on Adobe", or "explain this company's financials". This is analysis, not
  valuation — it does not decide what the company is worth (that's value-company).
---

# Read Fundamentals — is this company any good?

Fundamental analysis over the data already in `finance.db`. The **numbers come
from `analyze.py`** (a tested, read-only engine); your job is to **interpret and
teach**, not to recompute. The user is learning FSA, so every read should leave
them understanding *why* a metric matters, not just its value.

## Prerequisites
- Repo root `~/company-data-hub`, venv active (`source venv/bin/activate`).
- The company needs an **EDGAR statement history** for the trend analysis. If
  it's missing, run the `company-data` skill first
  (`python scrape_edgar_financials.py --company "<Name>"`).

## Steps

### 1. Get the computed analysis
```bash
python analyze.py --company "<name-or-ticker>"        # human-readable report
python analyze.py --company "<name-or-ticker>" --json  # if you want the raw numbers
```
If it prints "No EDGAR statement history", stop and refresh via `company-data`
first, then retry.

### 2. Interpret across four lenses (don't just restate the numbers)
Read the report and tell the story in each dimension. For a learner, pair each
with a one-line "why this matters":

- **Profitability & its direction** — operating/net/FCF margins over the window.
  Rising or falling? *Why it matters: margins show pricing power and operating
  leverage; the direction matters more than the level.*
- **Returns on capital** — ROE, ROA, and whether they're holding up as the equity
  base grows. *Why it matters: a great business compounds capital at high returns;
  falling ROE on a fattening balance sheet can just mean idle cash.*
- **Balance-sheet strength** — current ratio, liabilities/equity, equity ratio
  trend. *Why it matters: survivability (Philosophy #1) — leverage is what turns
  a bad year fatal.*
- **Quality of earnings** — the flags block: cash conversion (FCF/NI), accrual
  ratio, dilution, capex intensity. *Why it matters: profit that never becomes
  cash is the classic red flag; this is how you catch it.*

### 3. Call out the tension
The best insight is usually where two lines disagree — e.g. rising operating
margin but *falling* FCF conversion because capex is ramping. Name that tension
explicitly and what it implies (heavy reinvestment now for growth later, at the
cost of near-term free cash).

### 4. Deliver a health verdict (not a price)
End with a compact verdict:
- **Profitable?** yes/no and how durably.
- **Healthy?** balance sheet + quality flags, green/amber/red.
- **Direction?** improving / stable / deteriorating, with the one metric that
  most drives that call.
Then: "to decide whether it's *worth buying* at today's price, run
**value-company**." Keep this skill about the business, not the stock price.

## Notes
- **Two data sources, different jobs:** the EDGAR series (FY####) gives the
  multi-year *trend*; the Yahoo snapshot gives *current* market ratios (P/E, PEG,
  gross margin, beta). Treat Yahoo values as as-stored — their scaling is
  inconsistent and some points are unreliable (e.g. dividend_yield), so don't
  over-precisely interpret a single snapshot number.
- Some items aren't available from stored statement data (gross margin trend,
  quick ratio, interest coverage) because they need line items EDGAR's
  standardized set omits. Say so rather than inventing them.
- Ground survivability/quality comments in `PHILOSOPHY.md` where natural, but keep
  the teaching concrete and tied to this company's actual numbers.
