# Finance company-data agent — project handoff brief

A working brief to continue this project in Claude Cowork. It captures the goal,
the decisions made (and why), what's already built and tested, and the open next
steps. Two files accompany this brief: `store.py` and `companies.json`.

---

## Goal

Build a personal agent that maintains a growing database of information about a
set of companies and lets the owner ask natural-language questions against it
(e.g. "what's the news about SpaceX?", "which of my companies are exposed to
supply-chain risk, and why?").

Requirements that shaped the design:
- A curated list of companies is provided as a JSON file.
- The agent gathers all available info per company: a big one-time backfill,
  then small daily increments.
- Data is text + numerical only (news, filings, metrics). Real market data from
  Interactive Brokers (IB) is a **future** phase, not now.
- Must be as **cost-efficient** as possible.
- Owner is the only writer (the agent) and the only reader (one person).

---

## Decisions made, and the reasoning

**Architecture chosen (the cheapest, simplest option):**
SQLite database + a daily scraper that appends to it + a single query script.
No MCP server, no embeddings, no vector database, no hosted server.

Why this and not the fancier options:
- **One writer, one reader** → a server or MCP layer buys nothing. Those exist to
  share data across many clients or expose tools to other agents. Not needed here.
  (MCP also doesn't cost extra *money* — LLM tokens cost the same either way; its
  cost is setup/maintenance. Revisit MCP only if sharing with others/agents later.)
- **Text + numbers at modest scale** → SQLite is the sweet spot: one file, no
  server, fast with indexes, handles many GB, good at both text and numbers.
- **Conceptual questions** ("supply-chain risk") are handled by having the LLM
  *read* the content, not by keyword matching. Keyword/FTS is too literal;
  embeddings only *retrieve*, they don't *judge*.
- **Embeddings are deferred.** Because every record is tagged to a company, most
  retrieval is a plain `WHERE company = ?`. Add embeddings only if the company
  universe grows too large to fit candidate text in one LLM call.

**The trick that keeps conceptual queries cheap:** maintain a short **summary
(dossier) per company**, refreshed when new data arrives. A broad question then
loads a few hundred short summaries into one LLM call instead of thousands of raw
articles. Expensive "reading" happens once, incrementally at ingestion (small
daily delta), so per-question cost stays a cent or two — or free on a local model.

**LLM choice:** local model via Ollama for $0 queries, or a cheap API for pennies.
It's a one-function swap; nothing else in the system depends on it.

**Compute/scheduling:** GitHub Actions cron (free) runs the daily scraper. No
always-on server needed for the news/metrics phase.

**Backup (when the DB starts growing):** don't commit the `.db` into git (binary
bloat). Use Litestream (continuous replication to cheap object storage) or move
the DB to Turso (hosted SQLite, same SQL).

**When to add complexity back — only if a real limit forces it:**
- Too many companies to fit one LLM call → add a keyword pre-filter, then
  embeddings if still too big.
- Want to query from a phone / share it → wrap the query script in a small endpoint.
- Share with other people or agents → that's when an MCP server earns its keep.

---

## Current state — DONE

The **database/storage layer is built and tested** (`store.py`). It is pure
storage; no query mechanism is baked in, so the query approach stays open.

Schema (all tables hang off `companies`):
- `companies` — one row per company from the JSON list. Accepts plain names or
  objects; unknown fields are kept in a `meta` JSON column. Has a `summary`
  column (the dossier slot, currently empty) and a `last_fetched` watermark.
- `news` — text items, deduped by `(company_id, url)`.
- `metrics` — numbers in long/tidy form: `(company, metric, period, value, unit)`.
  Upserts on `(company, metric, period)`, so revised figures overwrite in place.
- `filings` — longer documents (10-K, calls), deduped by `(company_id, url)`.
- Indexes on `(company_id, date)` for fast per-company lookups.

Verified behaviors: idempotent ingestion (re-running the backfill or a retried
day never duplicates), metric upsert-in-place, per-company `last_fetched`
watermark for incremental daily pulls.

Run it:
```bash
python store.py --init                 # create finance.db
python store.py --load industries.json # load industries + companies
python store.py --stats                # inspect
```

The scraper will call these helpers per company: `add_news(...)`,
`add_metric(...)`, `add_filing(...)`, `set_summary(...)`, `set_last_fetched(...)`.

---

## Open next steps — TODO

1. **Provide the real `companies.json`** (the actual company list to track).
2. **Build the daily scraper** — a `sources.yaml` of feeds/URLs, a fetch script
   (prefer RSS + `trafilatura` for article text; prefer structured data APIs for
   numbers so no LLM is needed to extract them), and a GitHub Actions cron
   workflow. It calls the `store.py` helpers and uses the watermark to pull only
   new data each day.
3. **Decide the query method and build it** — the recommended cheap path is a
   single `ask.py` that loads company summaries (all, or a `WHERE`-filtered
   subset), makes one LLM call, and prints the answer with sources. Default to a
   local model so queries are free.
4. **Add the enrichment step** that fills each company's `summary` from its new
   data (one cheap/local LLM pass over the small daily delta). This is what makes
   broad conceptual questions cheap.
5. **Set up backup** (Litestream or Turso) once the DB grows.
6. **Future: Interactive Brokers** for real market data. Note this breaks the
   free-serverless model — the IB API needs an authenticated IB Gateway session
   that can't live in GitHub Actions, so it requires a small always-on worker
   (cheap VPS / home box) writing prices into the same SQLite (a `prices` table,
   same long/tidy idea). Real-time data may need paid IB subscriptions; historical
   is often cheaper/free.

---

## Files in this handoff
- `store.py` — the tested SQLite storage layer (schema + idempotent ingestion).
- `companies.json` — sample input format (replace with the real list).
