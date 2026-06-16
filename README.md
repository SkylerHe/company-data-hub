# company-data-hub

A personal, low-cost hub that gathers data on the companies you track — organized
across industries — to support equity research and financial analysis. The goal:
collect text + numerical data (news, filings, financial metrics) and answer
natural-language questions against it.

**What's built today (this repo):** the data-collection foundation — a SQLite
storage layer and a daily news scraper, with companies grouped into industries.

**Not built yet:** the parts that turn collected data into actual research —
financial metrics + SEC filings ingestion, the per-company summary/dossier, and
the query/analysis layer. Those are scaffolded (tables + helpers exist) and
tracked in `HANDOFF.md`. So right now this *gathers the inputs* for equity
research; it does not yet *perform* analysis.

This corresponds to step 2 of `HANDOFF.md`. The query layer (a simple `ask.py`
vs. an MCP server) is intentionally left open.

## Files
- `store.py` — SQLite storage layer (now with industries; tested).
- `industries.json` — **the single source of truth**: every industry with its companies (a company may appear under several). A flat list shape is still accepted by `--load`, but this repo tracks everything here.
- `sources.yaml` — where the scraper looks for news, per company and per industry.
- `scrape.py` — the daily scraper (RSS via feedparser + full text via trafilatura).
- `requirements.txt` — `feedparser`, `trafilatura`, `PyYAML`.
- `daily-scrape.yml` — GitHub Actions cron → put at `.github/workflows/daily-scrape.yml`.
- `test_scrape_offline.py`, `test_industries_offline.py` — offline tests.

## Run locally
```bash
pip install -r requirements.txt
python store.py --init                  # create finance.db
python store.py --load industries.json  # load industries + companies (auto-detected)
python scrape.py                        # daily job: pull new news for every company
python store.py --stats                 # inspect what landed
```

`--load` auto-detects the file shape: a JSON object → industry-first; a JSON list →
flat company list. Both can be mixed across runs (idempotent).

## Industries (how grouping helps searching)
Companies are tagged with one or more industries via a many-to-many model
(`industries` + `company_industries`). This is what makes industry-scoped queries
cheap: filter to an industry, then load only those companies' summaries into one
LLM call.

```bash
python store.py --in-industry "Artificial Intelligence"   # -> NVIDIA, Microsoft, Alphabet, ...
```

In code, `store.companies_in_industry(db, name)` is the search primitive the query
layer will use; `store.industries_of(db, company)` is the reverse lookup.

Edit `industries.json` to define the industries you track and the companies under
each (a company may appear under several — e.g. NVIDIA in Semiconductors + AI). You
can also attach an **industry-level feed once** in `sources.yaml` under `industries:`
and it applies to every member company.

Handy flags:
```bash
python scrape.py --company NVIDIA      # one company
python scrape.py --no-fetch-text       # title + RSS summary only (fast, no article fetch)
python scrape.py --since 2026-06-01    # ignore watermark; pull back to a date (backfill)
python scrape.py --dry-run             # parse everything, write nothing
```

## How it stays cheap & correct
- **Google News RSS** per company (built from the `query` in `sources.yaml`) gives
  broad coverage with zero API keys — works even for private companies like SpaceX.
  You can add explicit company/IR feeds under `feeds:`.
- **Watermark** (`last_fetched`) means daily runs only process new items.
- **Idempotent**: dedup is `UNIQUE(company_id, url)`, so re-runs and overlapping
  feeds never create duplicates. Tracking params (utm_, etc.) are stripped first.
- **No LLM in the scraper** — it only fetches and stores text. The expensive
  "reading" is deferred to the (later) enrichment + query steps.
- **Originals are kept** — the full article text is stored verbatim in
  `news.content` (plain text, not HTML: cheap to store, easy to search). Nothing
  truncates or summarizes it, so you can always pull the original back up:
  ```bash
  python store.py --show "https://www.example.com/the-article"
  ```
  In code, `store.get_news(db, url=...)` returns the item with its full text — the
  primitive the query layer uses when you ask the agent to "show the original."

## Verified
`test_scrape_offline.py` (9 checks) covers dedup, idempotency, watermark
filter + advance, URL cleaning, full-text vs. summary, dry-run, and full-text
retrieval.
`test_industries_offline.py` (7 checks) covers industry-first load, multi-membership,
`companies_in_industry`, idempotent reload, and industry-level feed routing.
Both stub feedparser/trafilatura because the build sandbox is offline.

**You still need one real online run** to confirm live feeds + article extraction:
run the local steps above on your machine (or trigger the workflow manually via the
Actions tab) and check `--stats` shows news rows.

## Two known notes
1. **WAL + some mounted/network filesystems** can throw `disk I/O error` (seen on
   the build sandbox). Normal local disks and GitHub Actions are fine. If you ever
   hit it, run on a local path or change `journal_mode` in `store.py:get_db`.
2. **CI persistence** uses `actions/cache` for `finance.db` (free, no secrets).
   It's safe because ingestion is idempotent, but it's not a durable store —
   move to Litestream or Turso (HANDOFF step 5) once the data matters.

## Next decision (deferred)
Query method: a single `ask.py` (cheapest, local-model-friendly) or an MCP server
(only worth it if you'll share with other people/agents). Pick when ready.
