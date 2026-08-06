---
name: value-company
description: >-
  Estimate what a single company is worth and whether today's price offers a
  margin of safety — a multi-method valuation (2-stage DCF, CAPM/WACC, reverse
  DCF, peer-median comps, bear/base/bull scenarios) that ends in a buy / hold /
  avoid verdict and, on request, an editable Excel model. Branches by business
  type: operating companies (products/services) are valued on free cash flow;
  banks/financials on ROE & P/B instead, since a bank's FCF is meaningless.
  Trigger on requests
  like "what's MSFT worth?", "value Nvidia", "is Costco a buy at this price?",
  "run a DCF on Adobe", "build me a valuation model for AAPL". This is valuation,
  not health analysis — for "is this a good business?" use read-fundamentals.
---

# Value Company — what is it worth, and is it cheap?

Intrinsic-value estimation over the data already in `finance.db`. The **numbers
come from `valuation.py`** (a tested, read-only engine); the **editable model
comes from `report.py`**. Your job is to run them, interpret the result against
the user's investing philosophy, and be honest that a valuation is a *model, not
a fact*. The user is learning — make them understand what drives the number.

## Prerequisites
- Repo root `~/company-data-hub`, venv active (`source venv/bin/activate`).
- The company needs an **EDGAR FCF history** (for the DCF) and a **current price
  + Yahoo snapshot** (for shares, debt, beta, comps). If the engine says data is
  missing, run the **`company-data`** skill first, then retry.
- US filers only for the DCF — a foreign/ADR name with no 10-K has no stored FCF
  and can only be discussed via comps. Say so rather than forcing a DCF.

## Steps

### First: classify the business — the method depends on it
The right valuation method depends on *what kind of company* this is:
```bash
sqlite3 finance.db "SELECT name, ticker, sector FROM instruments WHERE ticker='<T>' OR name LIKE '%<q>%';"
```
- **Operating company** — sells products/services (Google, Costco, Nvidia, Apple).
  Value on **Free Cash Flow (FCF)** → follow the DCF steps 1–5 below.
- **Bank / financial** — a bank, insurer, or lender (Capital One, JPMorgan). **FCF is
  meaningless** here (no capex→FCF; the business *is* loans and deposits), so the FCF-DCF
  is nonsense → **skip it and use the "Bank / financial branch" below** (ROE & P/B).
  Tell by: sector is Financial/Financials, or stored `free_cash_flow` is absent/erratic and
  the balance sheet is dominated by loans & deposits.

### 1. Get the computed valuation
```bash
python valuation.py --company "<name-or-ticker>"          # human-readable
python valuation.py --company "<name-or-ticker>" --json    # raw numbers
```
If it prints "Can't value … need a positive FCF history", stop and refresh via
`company-data`, then retry. If FCF is negative/absent (early-stage, financials,
ADR), the DCF won't run — lean on comps and say the DCF isn't applicable.

**Assumptions are inputs, not truths.** The engine's defaults (risk-free 4.3%,
ERP 5%, terminal 2.5%, 25% required margin of safety) are documented starting
points. If the user has a view, pass it — and *always* sanity-check the
risk-free rate against reality, since it's the one most likely stale:
```bash
python valuation.py --company MSFT --growth 0.10 --rf 0.045 --mos 0.30
```

### 2. Read the result across the four methods (don't just quote the verdict)
Each method answers a different question — the insight is where they **disagree**:

- **2-stage DCF (bear/base/bull)** — *what the cash flows are worth* at your
  discount rate and growth. The scenario **range** is the answer, not the base
  point. Note which lever (growth vs WACC) the value is most sensitive to.
- **Reverse DCF** — *what the price already assumes.* This is the sharpest
  reality check: if the market is pricing 30% FCF growth against a 6% history,
  the DCF being "below price" isn't a mispricing — it's you and the market
  disagreeing about the future. Say which side the evidence supports.
- **Peer-median comps** — *what the market pays for similar businesses*
  (medians from same-industry names in the db). If comps say cheap but DCF says
  dear, the gap is usually growth expectations or multiple compression risk.
- **CAPM / WACC** — the discount rate itself; show how cost of equity was built
  (rf + β·ERP) so the user sees the assumption, not a black box.

### 3. Name the tension, then judge
The best output resolves the disagreement between methods into a view. E.g.
"DCF says 60% overvalued, but that's because trailing FCF is depressed by the
capex ramp and the reverse-DCF shows the market pricing continued high growth —
so the real question is whether that growth shows up, not whether the multiple
is wrong." Tie it to the price the user would pay.

### 4. Deliver a margin-of-safety verdict (grounded, not echoed)
End with the engine's verdict **plus your reasoning**:
- **Intrinsic range** (bear → bull) and where price sits in it.
- **Margin of safety** vs the required threshold — this is the buy discipline
  (PHILOSOPHY.md: survivability + don't overpay). No margin, no buy.
- **BUY / HOLD / AVOID**, with the single assumption that most drives the call
  and what would have to be true for the opposite conclusion.

### 5. (On request) build the editable Excel model
```bash
python report.py --company "<name-or-ticker>" [--out ~/Desktop/<T>_valuation.xlsx]
```
Produces a 4-sheet workbook (Summary · Assumptions · DCF · Comps) where the DCF
is **live Excel formulas** driven by an editable **Assumptions** sheet (yellow
cells). Tell the user: change the yellow inputs — WACC, growth, beta — and the
intrinsic value, upside, and margin of safety recompute. It's the tool for
*their own* stress-testing, which is the whole point when learning valuation.

### Bank / financial branch — value on ROE & P/B, not FCF
For banks/insurers, **ignore the FCF-DCF** (it's meaningless — a bank has no capex→FCF; its
cash flows *are* lending and deposits) and value the equity directly:
```bash
python analyze.py  --company "<bank>"     # ROE, P/B, book value, margins
python industry.py --company "<bank>"     # peer ROE / P/B comparison
```
- **ROE (return on equity)** is the engine of a bank's value — earnings ÷ shareholders'
  equity (its book value / net worth). High *and stable* ROE = quality.
- **P/B (price-to-book)** is the multiple banks trade on. Anchor: a bank is worth
  **book value × a justified P/B**, where **justified P/B ≈ (ROE − g) / (cost of equity − g)**.
  - Rule of thumb: **ROE above cost of equity (~10%) → deserves P/B > 1**; ROE below it →
    P/B < 1. A 15%-ROE bank at 1.0× book is *cheaper* than an 8%-ROE bank at 1.0× book —
    same price tag, very different value.
- **Book / tangible book value per share** — the net worth the P/B multiplies; prefer
  *tangible* (strip goodwill/intangibles).
- **Peer cross-check** — is its P/B low *for its ROE* versus other banks? That's the bank
  version of "cheap."
- **Durability inputs (if stored)** — net interest margin (NIM), efficiency ratio,
  charge-offs / non-performing loans, CET1 capital ratio. These decide whether the ROE
  lasts; say the DB lacks them rather than inventing.
- **Verdict:** judge price vs justified P/B and vs peer ROE/P/B — never an FCF margin of
  safety. If `valuation.py` prints a DCF for a bank, disregard it.

## Notes
- **A model, not a fact.** Always frame the output as conditional on the
  assumptions. Present the range and the margin of safety; never a single price
  target stated as truth. This is the evidence-based rule — every number traces
  to a stored value or a stated assumption.
- **FCF caveat.** Stored `free_cash_flow` is OCF − capex (post-interest), so the
  DCF discounts it at WACC as a teachable simplification, not textbook-pure FCFF.
  EV/EBITDA comps use EBIT (EDGAR has no D&A) → conservative. Mention when it matters.
- **Trailing FCF can mislead.** A recent capex surge (data-center buildout,
  reinvestment) depresses trailing FCF and drags the DCF down — flag it and
  consider `--growth` reflecting the normalized trajectory rather than a
  capex-dented CAGR.
- **Hand-off.** For "is this a good *business*?" (margins, balance sheet, quality
  of earnings) use **read-fundamentals** first; value-company assumes the
  business question is already answered and asks only about price.
