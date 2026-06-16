"""
store.py — SQLite storage layer for the company finance database.

Pure storage: schema, idempotent ingestion, a per-company fetch watermark, and
inspection. No query engine or embeddings here — that decision comes later, and
nothing in this file locks us into one approach.

Shape of the data (text + numerical, company-centric):
    companies           one row per company from your JSON list
    industries          industry/sector labels
    company_industries  many-to-many link (a company can be in several industries)
    news                text items tied to a company   (dedup by url)
    metrics             numbers in long/tidy form       (upsert by company+metric+period)
    filings             longer documents (10-K, calls)  (dedup by url)

Designed for: a big one-time backfill, then small daily increments. Re-running a
backfill or a retried day never creates duplicates.

Stdlib only — no pip install needed.

    python store.py --init                 # create the database
    python store.py --load industries.json # add/update industries + companies from JSON
    python store.py --stats                # see what's in it
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone

DB_PATH = "finance.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ----------------------------------------------------------------------------
# Connection + schema
# ----------------------------------------------------------------------------
def get_db(path: str = DB_PATH) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = WAL")  # safer concurrent reads while writing
    return db


def init_db(db: sqlite3.Connection) -> None:
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS companies (
            id                 INTEGER PRIMARY KEY,
            name               TEXT NOT NULL UNIQUE,
            ticker             TEXT,
            sector             TEXT,
            meta               TEXT,          -- JSON: any extra fields from your input
            summary            TEXT,          -- distilled dossier (filled in later)
            summary_updated_at TEXT,
            last_fetched       TEXT,          -- watermark for incremental daily pulls
            created_at         TEXT
        );

        CREATE TABLE IF NOT EXISTS news (
            id           INTEGER PRIMARY KEY,
            company_id   INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            source       TEXT,
            url          TEXT,
            title        TEXT,
            published_at TEXT,                -- ISO date, e.g. 2026-06-15
            content      TEXT,                 -- the FULL original article text, stored
                                               --   verbatim (plain text, not HTML) so you
                                               --   can always pull the original back up.
                                               --   Never summarized or truncated here.
            fetched_at   TEXT,
            UNIQUE(company_id, url)           -- same article can attach to >1 company
        );

        CREATE TABLE IF NOT EXISTS metrics (
            id          INTEGER PRIMARY KEY,
            company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            metric      TEXT NOT NULL,        -- 'revenue', 'employees', 'pe_ratio', ...
            period      TEXT NOT NULL,        -- 'FY2025', '2025-Q4', '2026-06-15'
            value       REAL,
            unit        TEXT,                 -- 'USD', 'count', '%'
            source      TEXT,
            fetched_at  TEXT,
            UNIQUE(company_id, metric, period)
        );

        CREATE TABLE IF NOT EXISTS filings (
            id          INTEGER PRIMARY KEY,
            company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            type        TEXT,                 -- '10-K', '8-K', 'earnings_call', ...
            url         TEXT,
            date        TEXT,
            title       TEXT,
            content     TEXT,                 -- the FULL original filing text, stored verbatim
            fetched_at  TEXT,
            UNIQUE(company_id, url)
        );

        CREATE INDEX IF NOT EXISTS idx_news_company_date
            ON news(company_id, published_at);
        CREATE INDEX IF NOT EXISTS idx_metrics_company
            ON metrics(company_id, metric);
        CREATE INDEX IF NOT EXISTS idx_filings_company_date
            ON filings(company_id, date);

        -- Industries: many-to-many, so one company can sit in several
        -- (e.g. Tesla in Automotive + Energy + AI).
        CREATE TABLE IF NOT EXISTS industries (
            id   INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS company_industries (
            company_id  INTEGER NOT NULL REFERENCES companies(id)  ON DELETE CASCADE,
            industry_id INTEGER NOT NULL REFERENCES industries(id) ON DELETE CASCADE,
            PRIMARY KEY (company_id, industry_id)
        );

        CREATE INDEX IF NOT EXISTS idx_ci_industry
            ON company_industries(industry_id);
        """
    )
    db.commit()


# ----------------------------------------------------------------------------
# Companies
# ----------------------------------------------------------------------------
def upsert_company(db, name, ticker=None, sector=None, meta=None) -> int:
    """Insert a company or update its fields if it already exists. Returns its id."""
    db.execute(
        """
        INSERT INTO companies (name, ticker, sector, meta, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            ticker = COALESCE(excluded.ticker, companies.ticker),
            sector = COALESCE(excluded.sector, companies.sector),
            meta   = COALESCE(excluded.meta,   companies.meta)
        """,
        (name, ticker, sector, json.dumps(meta) if meta else None, _now()),
    )
    db.commit()
    return company_id(db, name)


def company_id(db, name, create=True):
    row = db.execute("SELECT id FROM companies WHERE name = ?", (name,)).fetchone()
    if row:
        return row[0]
    if create:
        return upsert_company(db, name)
    return None


def load_companies_from_json(db, path) -> int:
    """Load companies from a JSON file. Accepts either:
        ["SpaceX", "NVIDIA"]
    or:
        [{"name": "NVIDIA", "ticker": "NVDA", "sector": "Semiconductors", ...}]
    Any keys beyond name/ticker/sector are kept in the `meta` JSON column.
    """
    with open(path) as f:
        items = json.load(f)

    n = 0
    for item in items:
        if isinstance(item, str):
            upsert_company(db, item)
        else:
            extra = {k: v for k, v in item.items()
                     if k not in ("name", "ticker", "sector")}
            upsert_company(
                db,
                name=item["name"],
                ticker=item.get("ticker"),
                sector=item.get("sector"),
                meta=extra or None,
            )
        n += 1
    print(f"Loaded/updated {n} companies from {path}")
    return n


# ----------------------------------------------------------------------------
# Industries (many-to-many with companies)
# ----------------------------------------------------------------------------
def upsert_industry(db, name) -> int:
    """Insert an industry if new; return its id."""
    db.execute("INSERT OR IGNORE INTO industries (name) VALUES (?)", (name,))
    db.commit()
    return industry_id(db, name)


def industry_id(db, name, create=True):
    row = db.execute("SELECT id FROM industries WHERE name = ?", (name,)).fetchone()
    if row:
        return row[0]
    if create:
        return upsert_industry(db, name)
    return None


def link_company_industry(db, company, industry) -> None:
    """Tag a company with an industry. Idempotent (PK on the pair)."""
    cid = company_id(db, company)
    iid = upsert_industry(db, industry)
    db.execute(
        "INSERT OR IGNORE INTO company_industries (company_id, industry_id) VALUES (?, ?)",
        (cid, iid),
    )
    db.commit()


def industries_of(db, company) -> list[str]:
    """Every industry a company belongs to."""
    cid = company_id(db, company, create=False)
    if cid is None:
        return []
    rows = db.execute(
        """
        SELECT i.name FROM industries i
        JOIN company_industries ci ON ci.industry_id = i.id
        WHERE ci.company_id = ? ORDER BY i.name
        """,
        (cid,),
    ).fetchall()
    return [r[0] for r in rows]


def companies_in_industry(db, industry) -> list[str]:
    """Every company in an industry — the search primitive for industry-scoped
    queries (load only these companies' summaries into one LLM call)."""
    iid = industry_id(db, industry, create=False)
    if iid is None:
        return []
    rows = db.execute(
        """
        SELECT c.name FROM companies c
        JOIN company_industries ci ON ci.company_id = c.id
        WHERE ci.industry_id = ? ORDER BY c.name
        """,
        (iid,),
    ).fetchall()
    return [r[0] for r in rows]


def load_industries_from_json(db, path) -> int:
    """Load an INDUSTRY-FIRST file. Two accepted shapes:

        {"Semiconductors": ["NVIDIA", "Taiwan Semiconductor"], "AI": ["NVIDIA"]}

    or, with per-company detail and optional industry metadata:

        {
          "Semiconductors": {
            "companies": [
              {"name": "NVIDIA", "ticker": "NVDA"},
              "Taiwan Semiconductor"
            ]
          }
        }

    A company listed under several industries is stored once and linked to each,
    which is how multi-membership works (e.g. NVIDIA in Semiconductors AND AI).
    """
    with open(path) as f:
        data = json.load(f)

    n_ind = 0
    seen_companies = set()
    for industry, body in data.items():
        upsert_industry(db, industry)
        n_ind += 1
        members = body.get("companies", []) if isinstance(body, dict) else body
        for item in members:
            if isinstance(item, str):
                name = item
                upsert_company(db, name)
            else:
                name = item["name"]
                extra = {k: v for k, v in item.items()
                         if k not in ("name", "ticker", "sector")}
                upsert_company(
                    db, name=name,
                    ticker=item.get("ticker"),
                    sector=item.get("sector"),
                    meta=extra or None,
                )
            link_company_industry(db, name, industry)
            seen_companies.add(name)
    print(f"Loaded/updated {n_ind} industries and "
          f"{len(seen_companies)} companies from {path}")
    return n_ind


def load(db, path) -> None:
    """Auto-detect the input shape and load it:
        list  -> flat company list      (load_companies_from_json)
        dict  -> industry-first mapping  (load_industries_from_json)
    """
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict):
        load_industries_from_json(db, path)
    else:
        load_companies_from_json(db, path)


# ----------------------------------------------------------------------------
# Ingestion (called by the scraper). All idempotent.
# ----------------------------------------------------------------------------
def add_news(db, company, source, url, title, published_at, content) -> int | None:
    """Add a news item. Returns new id, or None if this (company, url) already exists.

    `content` is stored verbatim — the full original article text — so it can be
    retrieved in full later (see get_news / `--show`)."""
    cid = company_id(db, company)
    cur = db.execute(
        """
        INSERT OR IGNORE INTO news
            (company_id, source, url, title, published_at, content, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (cid, source, url, title, published_at, content, _now()),
    )
    db.commit()
    return cur.lastrowid if cur.rowcount else None


def add_metric(db, company, metric, period, value, unit=None, source=None) -> None:
    """Add or update one numeric data point (long/tidy format)."""
    cid = company_id(db, company)
    db.execute(
        """
        INSERT INTO metrics (company_id, metric, period, value, unit, source, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(company_id, metric, period) DO UPDATE SET
            value = excluded.value, unit = excluded.unit,
            source = excluded.source, fetched_at = excluded.fetched_at
        """,
        (cid, metric, period, value, unit, source, _now()),
    )
    db.commit()


def add_filing(db, company, type, url, date, title, content) -> int | None:
    """Add a filing. `content` is the full original text, stored verbatim."""
    cid = company_id(db, company)
    cur = db.execute(
        """
        INSERT OR IGNORE INTO filings
            (company_id, type, url, date, title, content, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (cid, type, url, date, title, content, _now()),
    )
    db.commit()
    return cur.lastrowid if cur.rowcount else None


def set_summary(db, company, summary) -> None:
    """Store the distilled per-company dossier (populated later, by enrichment)."""
    cid = company_id(db, company)
    db.execute(
        "UPDATE companies SET summary = ?, summary_updated_at = ? WHERE id = ?",
        (summary, _now(), cid),
    )
    db.commit()


# ----------------------------------------------------------------------------
# Watermark — lets daily runs pull only what's new
# ----------------------------------------------------------------------------
def get_last_fetched(db, company):
    cid = company_id(db, company, create=False)
    if cid is None:
        return None
    row = db.execute("SELECT last_fetched FROM companies WHERE id = ?", (cid,)).fetchone()
    return row[0] if row else None


def set_last_fetched(db, company, when=None) -> None:
    cid = company_id(db, company)
    db.execute(
        "UPDATE companies SET last_fetched = ? WHERE id = ?",
        (when or _now(), cid),
    )
    db.commit()


# ----------------------------------------------------------------------------
# Retrieval — pull the full original text back up for reference
# ----------------------------------------------------------------------------
def get_news(db, url=None, news_id=None) -> list[dict]:
    """Return stored news item(s) including the FULL original text.

    Look up by exact `url` or by `news_id`. This is the primitive the query layer
    (or you, via `--show`) uses to show an original document verbatim later."""
    cols = ("id", "company", "title", "source", "url", "published_at", "content")
    sql = (
        "SELECT n.id, c.name, n.title, n.source, n.url, n.published_at, n.content "
        "FROM news n JOIN companies c ON n.company_id = c.id WHERE "
    )
    if news_id is not None:
        rows = db.execute(sql + "n.id = ?", (news_id,)).fetchall()
    elif url is not None:
        rows = db.execute(sql + "n.url = ?", (url,)).fetchall()
    else:
        return []
    return [dict(zip(cols, r)) for r in rows]


def show_news(db, url=None, news_id=None) -> None:
    """Print the full stored original text of a news item."""
    items = get_news(db, url=url, news_id=news_id)
    if not items:
        print("No stored news item matched.")
        return
    for it in items:
        print(f"# {it['title']}")
        print(f"{it['company']}  |  {it['source'] or '-'}  |  {it['published_at'] or '-'}")
        print(f"{it['url']}\n")
        print(it["content"] or "(no full text stored for this item)")


# ----------------------------------------------------------------------------
# Inspection / management
# ----------------------------------------------------------------------------
def stats(db) -> None:
    counts = {
        t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("companies", "industries", "news", "metrics", "filings")
    }
    print("Row counts:")
    for t, c in counts.items():
        print(f"  {t:<12} {c}")

    ind_rows = db.execute(
        """
        SELECT i.name, COUNT(ci.company_id)
        FROM industries i
        LEFT JOIN company_industries ci ON ci.industry_id = i.id
        GROUP BY i.id ORDER BY i.name
        """
    ).fetchall()
    if ind_rows:
        print("\nIndustries (company count):")
        for name, ncos in ind_rows:
            print(f"  {name:<24} {ncos}")

    rows = db.execute(
        """
        SELECT c.name,
               (SELECT COUNT(*) FROM news    n WHERE n.company_id = c.id),
               (SELECT COUNT(*) FROM metrics m WHERE m.company_id = c.id),
               c.last_fetched
        FROM companies c
        ORDER BY c.name
        """
    ).fetchall()
    if rows:
        print("\nPer company (news / metrics / industries / last_fetched):")
        for name, nnews, nmetrics, lf in rows:
            inds = ", ".join(industries_of(db, name)) or "-"
            print(f"  {name:<20} {nnews:>4} / {nmetrics:>4}   {inds:<28} {lf or '-'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Finance database storage layer")
    ap.add_argument("--init", action="store_true", help="create the database schema")
    ap.add_argument("--load", metavar="JSON",
                    help="load a flat company list OR an industry-first mapping "
                         "(auto-detected)")
    ap.add_argument("--in-industry", metavar="NAME",
                    help="list the companies in an industry, then exit")
    ap.add_argument("--stats", action="store_true", help="show row counts")
    ap.add_argument("--show", metavar="URL",
                    help="print the full stored original text of a news item by URL")
    args = ap.parse_args()

    if not (args.init or args.load or args.in_industry or args.stats or args.show):
        ap.print_help(sys.stderr)
        sys.exit(1)

    db = get_db()
    init_db(db)  # safe to call every time (IF NOT EXISTS)
    if args.load:
        load(db, args.load)
    if args.in_industry:
        names = companies_in_industry(db, args.in_industry)
        print(f"{args.in_industry}: " + (", ".join(names) if names else "(none)"))
    if args.stats:
        stats(db)
    if args.show:
        show_news(db, url=args.show)
