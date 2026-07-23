---
name: map-industry
description: >-
  Compare a company against its industry peers, or survey a whole industry's
  landscape — a side-by-side of size, growth, margins, ROE, and valuation
  multiples (P/E, P/S, EV/EBITDA, P/B) drawn from the same finance.db, with the
  leaders on each axis and where a given name sits vs. the peer median. Trigger
  on requests like "how does NVDA compare to other chip stocks?", "map the
  semiconductor industry", "who's the cheapest cloud name?", "which defense
  stock has the best margins?", "show me AMD's peers". This is *relative*
  analysis across companies — for one company's health use read-fundamentals,
  and for one company's intrinsic worth use value-company.
---

# Map Industry — how does it stack up against its peers?

Relative valuation and competitive comparison over the data already in
`finance.db`. The **numbers come from `industry.py`** (a read-only engine that
reuses the same EDGAR series + Yahoo snapshot the other skills use); your job is
to **read the landscape and teach**, not to recompute. The user is learning, so
tie the comparison back to *why* an axis matters and what the peer spread implies.

## When to use which skill (don't mix them up)
- **read-fundamentals** → is *this one* company healthy? (one company, absolute)
- **value-company** → what is *this one* company worth? (one company, intrinsic)
- **map-industry** → how does it compare to *others*, or what's the whole group
  like? (many companies, relative)

They compose: map the industry to find the interesting names, then
read-fundamentals / value-company on the one that stands out.

## Prerequisites
- Repo root `~/company-data-hub`, venv active (`source venv/bin/activate`).
- Comparison quality depends on peers having data. Fundamentals (growth, margins,
  ROE) need an **EDGAR history**; multiples need a **Yahoo snapshot**. Names with
  neither (foreign/ADR with no 10-K, or a peer never refreshed) show as `-`. If a
  peer you care about is blank, refresh it with the **`company-data`** skill.
- Industries live in the `company_industries` linkage (23 industries, ~11 names
  each). ETFs/funds tagged to an industry are excluded automatically — this is a
  company-vs-company comparison.

## Steps

### 1. Get the comparison
```bash
python industry.py --industry Semiconductors          # survey one industry
python industry.py --company NVIDIA                    # map every industry a name is in
python industry.py --industry "Cloud & Software" --json # raw numbers
```
Partial industry names work (`--industry chip` won't, but `--industry Semi`
will). `--company` marks the focus name with `►` and adds a "vs peers" block for
it in each of its industries.

If nothing maps, the name/industry isn't tracked — check the spelling or list
industries: `sqlite3 finance.db "SELECT name FROM industries ORDER BY name;"`.

### 2. Read the landscape across four axes (don't just dump the table)
The table is sorted by size (market cap). Tell the story in each dimension:

- **Size** — market cap & revenue. Who's the gorilla, who's the minnow? Scale
  often buys durability and pricing power. *Why it matters: a small peer growing
  fast is a different bet than the incumbent.*
- **Growth** — revenue CAGR over the EDGAR window. Who's actually expanding?
  *Why it matters: growth is what most of a valuation multiple is paying for.*
- **Profitability** — operating margin, net margin, ROE. Who converts revenue to
  profit best, and who earns the highest return on equity? *Why it matters: high,
  stable margins signal a moat; ROE is the quality-of-business headline.*
- **Valuation** — P/E, P/S, EV/EBITDA, P/B vs. the **peer median** (the last row).
  *Why it matters: "cheap" only means something relative to peers — this is the
  comps method in action.*

### 3. Find the tension — quality vs. price
The best insight is usually a mismatch between an axis and its multiple:
- A name that leads on margins/ROE/growth **but trades below the median multiple**
  is the classic "quality at a relative discount" — flag it (it's exactly what
  the focus block calls out, e.g. a leader that's *cheaper* on P/E than peers).
- A laggard on fundamentals trading at a **premium** multiple is the opposite —
  priced for a turnaround that may not come.
Name the specific companies and numbers, not generalities.

### 4. Deliver a landscape verdict (relative, not absolute)
Close with:
- **The leader(s)** — who dominates on size/growth/profitability (the engine's
  "Who leads on what" block).
- **The relative-value standout** — cheapest on P/E / EV/EBITDA *given* its
  quality, and the richest (priced for perfection).
- **Where the focus company sits** — ahead of / behind the median on each axis,
  and whether its multiple looks earned.
Then hand off: "to judge whether the standout is *actually* cheap (not just cheap
vs. peers), run **value-company**; to check its financial health, run
**read-fundamentals**." Keep this skill about the *field*, not a single verdict.

## Notes
- **Two sources, two jobs:** fundamentals (growth/margins/ROE) are from EDGAR
  statements — consistent and multi-year; multiples (P/E, P/S, EV/EBITDA, P/B)
  are the *current* Yahoo snapshot. Say which you're leaning on.
- **The median is deliberately robust.** It's used instead of the mean precisely
  so one bad Yahoo point (e.g. a nonsensical EV/EBITDA or P/B in the thousands —
  a known snapshot bug) barely moves the summary. Still, don't over-interpret a
  single wild multiple on one peer — call it out as suspect rather than real.
- **Relative ≠ absolute.** Comps tell you cheap/dear *versus peers*; if the whole
  industry is over- or under-valued, the median inherits that. Pair with
  value-company's DCF when the question is "is this genuinely cheap?" (this is
  the comps-vs-DCF limitation the user already learned).
- **Foreign/ADR peers** (TSM, ASML, ARM…) have Yahoo multiples but no stored
  10-K, so their fundamentals show `-`. Compare them on multiples only, and say so.
- Ground competitive/quality comments concretely in the numbers on screen; where
  natural, connect durability/moat to `PHILOSOPHY.md`.
