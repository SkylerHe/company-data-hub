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
        -- One row per tradable instrument: stock, ETF, fund, bond, commodity, crypto...
        -- `asset_class` is WHAT it is; `fund_strategy` (index/active/NULL) is HOW a fund
        -- is run (SPY = etf + index; ARKQ = etf + active; a stock = stock + NULL).
        CREATE TABLE IF NOT EXISTS instruments (
            id                 INTEGER PRIMARY KEY,
            name               TEXT NOT NULL UNIQUE,
            ticker             TEXT,
            asset_class        TEXT NOT NULL DEFAULT 'stock' REFERENCES asset_classes(name),
            fund_strategy      TEXT,          -- 'index' | 'active' | NULL (only for funds)
            currency           TEXT DEFAULT 'USD',
            exchange           TEXT,
            sector             TEXT,
            meta               TEXT,          -- JSON: any extra fields from your input
            summary            TEXT,          -- distilled dossier (filled in later)
            summary_updated_at TEXT,
            last_fetched       TEXT,          -- watermark for incremental daily pulls
            created_at         TEXT
        );

        CREATE TABLE IF NOT EXISTS asset_classes (
            id          INTEGER PRIMARY KEY,
            name        TEXT NOT NULL UNIQUE,
            description TEXT
        );
        INSERT OR IGNORE INTO asset_classes (name, description) VALUES
            ('stock',     'Individual company common stock / ADR'),
            ('etf',       'Exchange-traded fund'),
            ('fund',      'Closed-end / interval / mutual fund'),
            ('bond',      'Fixed income (bond fund or individual bond)'),
            ('reit',      'Real estate investment trust'),
            ('commodity', 'Commodity fund (gold, oil, ...)'),
            ('crypto',    'Crypto asset / spot crypto fund'),
            ('index',     'Index level (not directly tradable)'),
            ('cash',      'Cash / money-market / T-bill');

        CREATE TABLE IF NOT EXISTS news (
            id           INTEGER PRIMARY KEY,
            company_id   INTEGER NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
            source       TEXT,
            url          TEXT,
            title        TEXT,
            published_at TEXT,                -- ISO date, e.g. 2026-06-15
            content      TEXT,                 -- the FULL original article text, stored
                                               --   verbatim (plain text, not HTML) so you
                                               --   can always pull the original back up.
                                               --   Never summarized or truncated here.
            fetched_at   TEXT,
            UNIQUE(company_id, url)           -- same article can attach to >1 instrument
        );

        -- Dense daily OHLCV time-series. One row per (instrument, date) — NOT the tall
        -- metrics table (that stored 5 EAV rows/day). Range queries are index-only scans.
        CREATE TABLE IF NOT EXISTS prices (
            instrument_id INTEGER NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
            date          TEXT NOT NULL,      -- 'YYYY-MM-DD'
            open          REAL,
            high          REAL,
            low           REAL,
            close         REAL,
            volume        REAL,
            ma_20         REAL,      -- trailing 20-day SMA of close (short-term)
            ma_50         REAL,      -- 50-day SMA (medium-term)
            ma_200        REAL,      -- 200-day SMA (long-term / trend)
            source        TEXT,
            fetched_at    TEXT,
            PRIMARY KEY (instrument_id, date)
        );

        -- Sparse fundamentals only (revenue, EPS, margins, ratios). Prices live in `prices`.
        CREATE TABLE IF NOT EXISTS metrics (
            id          INTEGER PRIMARY KEY,
            company_id  INTEGER NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
            metric      TEXT NOT NULL,        -- 'revenue', 'eps_ttm', 'pe_ratio', ...
            period      TEXT NOT NULL,        -- 'FY2025', '2025-Q4', '2026-06-15'
            value       REAL,
            unit        TEXT,                 -- 'USD', 'count', '%'
            source      TEXT,
            fetched_at  TEXT,
            UNIQUE(company_id, metric, period)
        );

        CREATE TABLE IF NOT EXISTS filings (
            id          INTEGER PRIMARY KEY,
            company_id  INTEGER NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
            type        TEXT,                 -- '10-K', '8-K', 'earnings_call', ...
            url         TEXT,
            date        TEXT,
            title       TEXT,
            content     TEXT,                 -- the FULL original filing text, stored verbatim
            fetched_at  TEXT,
            UNIQUE(company_id, url)
        );

        -- Research papers / strategy literature (AQR, SSRN, journals). Like `filings`,
        -- keep the metadata + optional full text verbatim so every strategy traces back
        -- to its source research. `strategy` loosely links to a Strategy Research entry
        -- (S1/S2) or a factor; `topic` tags it (trend-following, value, tax-aware, ...).
        CREATE TABLE IF NOT EXISTS papers (
            id          INTEGER PRIMARY KEY,
            title       TEXT NOT NULL,
            authors     TEXT,
            source      TEXT,                 -- AQR, SSRN, Journal of Finance, ...
            url         TEXT,
            year        INTEGER,
            topic       TEXT,                 -- 'trend-following', 'value', 'tax-aware', ...
            strategy    TEXT,                 -- optional link: 'S1', 'S2', 'screener', factor
            summary     TEXT,                 -- why it matters / key takeaway
            content     TEXT,                 -- full text if fetched (verbatim), else NULL
            read_status TEXT DEFAULT 'unread',-- 'unread' | 'read'
            added_at    TEXT,
            UNIQUE(title, source)
        );

        -- Option-chain snapshots: one row per (underlying, expiry, strike, right)
        -- PER SNAPSHOT. Unlike `prices` (one row/day), we keep every timestamped pull
        -- so a HISTORY of implied vol accumulates — that history is what later powers
        -- IV Rank / IV Percentile (is option premium cheap or rich vs. its own past?).
        -- `implied_vol` and the Greeks are stored as decimals (0.1905 = 19.05%,
        -- delta 0.42, ...), exactly as IBKR's model reports them. `opt_right` avoids
        -- the SQL keyword RIGHT.
        CREATE TABLE IF NOT EXISTS option_quotes (
            id               INTEGER PRIMARY KEY,
            instrument_id    INTEGER NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
            expiry           TEXT NOT NULL,     -- 'YYYY-MM-DD' option expiration
            strike           REAL NOT NULL,
            opt_right        TEXT NOT NULL,     -- 'C' | 'P'
            bid              REAL,
            ask              REAL,
            last             REAL,
            underlying_price REAL,              -- spot at snapshot time
            implied_vol      REAL,              -- decimal (0.1905 = 19.05%)
            delta            REAL,
            gamma            REAL,
            vega             REAL,              -- per 1.00 vol (÷100 for per-1%)
            theta            REAL,              -- per day
            rho              REAL,              -- per 1.00 rate (÷100 for per-1%)
            model_price      REAL,
            source           TEXT,              -- 'IBKR'
            snapshot_at      TEXT NOT NULL,     -- ISO timestamp of this pull
            UNIQUE(instrument_id, expiry, strike, opt_right, snapshot_at)
        );

        -- Common-size statements: each EDGAR line item as a fraction of its base
        -- (income & cash-flow ÷ revenue, balance sheet ÷ total_assets), per fiscal
        -- year. DERIVED from the SEC/EDGAR dollar rows in `metrics` — a materialized
        -- view rebuilt by store.recompute_common_size() after an EDGAR pull (like the
        -- moving averages after a price pull), not a separate data source. `pct` is a
        -- decimal (0.22 = 22%); `base_item` records which denominator was used.
        CREATE TABLE IF NOT EXISTS common_size (
            company_id  INTEGER NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
            statement   TEXT NOT NULL,     -- 'income' | 'balance' | 'cash_flow'
            line_item   TEXT NOT NULL,     -- e.g. 'net_income', 'total_liabilities'
            period      TEXT NOT NULL,     -- 'FY2024'
            pct         REAL,              -- line_item / base  (0.22 = 22%)
            base_item   TEXT NOT NULL,     -- 'revenue' | 'total_assets'
            computed_at TEXT,
            PRIMARY KEY (company_id, statement, line_item, period)
        );

        CREATE INDEX IF NOT EXISTS idx_news_company_date
            ON news(company_id, published_at);
        CREATE INDEX IF NOT EXISTS idx_papers_topic
            ON papers(topic);
        CREATE INDEX IF NOT EXISTS idx_prices_date
            ON prices(date);
        CREATE INDEX IF NOT EXISTS idx_metrics_company_metric_period
            ON metrics(company_id, metric, period);
        CREATE INDEX IF NOT EXISTS idx_filings_company_date
            ON filings(company_id, date);
        CREATE INDEX IF NOT EXISTS idx_option_quotes_lookup
            ON option_quotes(instrument_id, expiry, snapshot_at);
        CREATE INDEX IF NOT EXISTS idx_common_size_lookup
            ON common_size(company_id, period);
        CREATE INDEX IF NOT EXISTS idx_instruments_ticker
            ON instruments(ticker);
        CREATE INDEX IF NOT EXISTS idx_instruments_asset_class
            ON instruments(asset_class);

        -- Industries: many-to-many, so one instrument can sit in several
        -- (e.g. Tesla in Automotive + Energy + AI).
        CREATE TABLE IF NOT EXISTS industries (
            id   INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS company_industries (
            company_id  INTEGER NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
            industry_id INTEGER NOT NULL REFERENCES industries(id)  ON DELETE CASCADE,
            PRIMARY KEY (company_id, industry_id)
        );

        CREATE INDEX IF NOT EXISTS idx_ci_industry
            ON company_industries(industry_id);
        """
    )
    db.commit()
    # Migration: precomputed moving-average columns on `prices` (added after the
    # original schema). ALTER ADD COLUMN is a cheap metadata-only op; idempotent.
    have = {r[1] for r in db.execute("PRAGMA table_info(prices)")}
    for w in MA_WINDOWS:
        if f"ma_{w}" not in have:
            db.execute(f"ALTER TABLE prices ADD COLUMN ma_{w} REAL")
    db.commit()


# ----------------------------------------------------------------------------
# Companies
# ----------------------------------------------------------------------------
def upsert_company(db, name, ticker=None, sector=None, meta=None,
                   asset_class=None, fund_strategy=None, currency=None, exchange=None) -> int:
    """Insert an instrument or update its fields if it already exists. Returns its id.

    `asset_class` (stock/etf/fund/bond/commodity/crypto/...) and `fund_strategy`
    (index/active) classify what the instrument is; both default sensibly and only
    overwrite existing values when explicitly passed."""
    db.execute(
        """
        INSERT INTO instruments (name, ticker, sector, meta, asset_class,
                                 fund_strategy, currency, exchange, created_at)
        VALUES (?, ?, ?, ?, COALESCE(?, 'stock'), ?, COALESCE(?, 'USD'), ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            ticker        = COALESCE(excluded.ticker,        instruments.ticker),
            sector        = COALESCE(excluded.sector,        instruments.sector),
            meta          = COALESCE(excluded.meta,          instruments.meta),
            fund_strategy = COALESCE(excluded.fund_strategy, instruments.fund_strategy),
            exchange      = COALESCE(excluded.exchange,      instruments.exchange)
        """,
        (name, ticker, sector, json.dumps(meta) if meta else None,
         asset_class, fund_strategy, currency, exchange, _now()),
    )
    # asset_class/currency are only set on first insert (COALESCE default); update them
    # explicitly when the caller passes a value, so reclassification is possible.
    if asset_class is not None:
        db.execute("UPDATE instruments SET asset_class=? WHERE name=?", (asset_class, name))
    if currency is not None:
        db.execute("UPDATE instruments SET currency=? WHERE name=?", (currency, name))
    db.commit()
    return company_id(db, name)


def company_id(db, name, create=True):
    row = db.execute("SELECT id FROM instruments WHERE name = ?", (name,)).fetchone()
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
        SELECT c.name FROM instruments c
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


# OHLCV metric names -> column in the wide `prices` table. Legacy scraper code calls
# add_metric('price_close', ...); we transparently route those into `prices` so callers
# don't change and price data never bloats the sparse `metrics` table again.
_PRICE_FIELD = {
    "price_open": "open", "price_high": "high", "price_low": "low",
    "price_close": "close", "volume": "volume",
}


def add_metric(db, company, metric, period, value, unit=None, source=None) -> None:
    """Add or update one numeric data point.

    OHLCV metrics (price_open/high/low/close, volume) are routed to the wide `prices`
    table; everything else (revenue, EPS, ratios, ...) stays in the tidy `metrics` table.
    """
    cid = company_id(db, company)
    field = _PRICE_FIELD.get(metric)
    if field:
        # period is the trade date ('YYYY-MM-DD'); upsert the one OHLCV column.
        db.execute(
            f"""
            INSERT INTO prices (instrument_id, date, {field}, source, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(instrument_id, date) DO UPDATE SET
                {field} = excluded.{field},
                source  = COALESCE(excluded.source, prices.source),
                fetched_at = excluded.fetched_at
            """,
            (cid, period, value, source, _now()),
        )
        db.commit()
        return
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


def add_price(db, instrument, date, open=None, high=None, low=None, close=None,
              volume=None, source=None) -> None:
    """Upsert one day of OHLCV for an instrument into the wide `prices` table."""
    iid = company_id(db, instrument)
    db.execute(
        """
        INSERT INTO prices (instrument_id, date, open, high, low, close, volume, source, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(instrument_id, date) DO UPDATE SET
            open=excluded.open, high=excluded.high, low=excluded.low,
            close=excluded.close, volume=excluded.volume,
            source=excluded.source, fetched_at=excluded.fetched_at
        """,
        (iid, date, open, high, low, close, volume, source, _now()),
    )
    db.commit()


def get_prices(db, instrument, start=None, end=None, field="close"):
    """Return [(date, value), ...] for one price field, optionally within [start, end]."""
    iid = company_id(db, instrument, create=False)
    if iid is None:
        return []
    q = f"SELECT date, {field} FROM prices WHERE instrument_id=?"
    args = [iid]
    if start:
        q += " AND date >= ?"; args.append(start)
    if end:
        q += " AND date <= ?"; args.append(end)
    q += " ORDER BY date"
    return db.execute(q, args).fetchall()


# ----------------------------------------------------------------------------
# Option-chain snapshots (implied vol + Greeks over time)
# ----------------------------------------------------------------------------
def add_option_quote(db, underlying, expiry, strike, opt_right, *, bid=None, ask=None,
                     last=None, underlying_price=None, implied_vol=None, delta=None,
                     gamma=None, vega=None, theta=None, rho=None, model_price=None,
                     source=None, snapshot_at=None) -> None:
    """Upsert one option-chain snapshot row (keyed by underlying+expiry+strike+right+time).

    `underlying` is the stored instrument name or ticker; `opt_right` is 'C'/'P'
    (first letter is taken, case-insensitive). Re-running the same pull at the same
    `snapshot_at` overwrites in place; a later pull adds a new timestamped row so IV
    history builds up. Vol/Greeks are stored as decimals, as IBKR reports them."""
    iid = company_id(db, resolve_instrument(db, underlying) or underlying)
    r = (opt_right or "").strip().upper()[:1]
    ts = snapshot_at or _now()
    db.execute(
        """
        INSERT INTO option_quotes
            (instrument_id, expiry, strike, opt_right, bid, ask, last, underlying_price,
             implied_vol, delta, gamma, vega, theta, rho, model_price, source, snapshot_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(instrument_id, expiry, strike, opt_right, snapshot_at) DO UPDATE SET
            bid=excluded.bid, ask=excluded.ask, last=excluded.last,
            underlying_price=excluded.underlying_price, implied_vol=excluded.implied_vol,
            delta=excluded.delta, gamma=excluded.gamma, vega=excluded.vega,
            theta=excluded.theta, rho=excluded.rho, model_price=excluded.model_price,
            source=excluded.source
        """,
        (iid, expiry, strike, r, bid, ask, last, underlying_price, implied_vol,
         delta, gamma, vega, theta, rho, model_price, source, ts),
    )
    db.commit()


def resolve_instrument(db, query):
    """Return the instrument `name` for a name or ticker query, else None.
    (Small local twin of analyze.resolve_company so store stays import-free.)"""
    row = db.execute(
        "SELECT name FROM instruments WHERE name = ? OR ticker = ? LIMIT 1",
        (query, query),
    ).fetchone()
    return row[0] if row else None


def get_option_quotes(db, underlying, expiry=None, opt_right=None, latest_only=True):
    """Return option-quote rows for an underlying (newest snapshot first).

    latest_only=True keeps just the most recent snapshot per (expiry, strike, right)."""
    name = resolve_instrument(db, underlying)
    iid = company_id(db, name, create=False) if name else None
    if iid is None:
        return []
    q = "SELECT * FROM option_quotes WHERE instrument_id=?"
    args = [iid]
    if expiry:
        q += " AND expiry=?"; args.append(expiry)
    if opt_right:
        q += " AND opt_right=?"; args.append(opt_right.strip().upper()[:1])
    q += " ORDER BY snapshot_at DESC, expiry, strike"
    db.row_factory = sqlite3.Row
    rows = db.execute(q, args).fetchall()
    if not latest_only:
        return rows
    seen, out = set(), []
    for row in rows:                        # rows are newest-first, so first wins
        key = (row["expiry"], row["strike"], row["opt_right"])
        if key not in seen:
            seen.add(key)
            out.append(row)
    return out


# Trailing simple moving averages precomputed into the prices table (short/med/long).
MA_WINDOWS = (20, 50, 200)


def recompute_moving_averages(db, instrument, windows=MA_WINDOWS) -> int:
    """Recompute trailing simple moving averages (SMA) of `close` for one instrument
    into the prices `ma_<w>` columns. SMA_w at a date = mean of the last w closes up to
    and including that day (NULL until w closes exist). Recomputes the whole series, so
    it's idempotent — safe to call after every price pull. Returns rows updated."""
    iid = company_id(db, instrument, create=False)
    if iid is None:
        return 0
    rows = db.execute(
        "SELECT date, close FROM prices WHERE instrument_id=? AND close IS NOT NULL "
        "ORDER BY date", (iid,)).fetchall()
    if not rows:
        return 0
    dates = [r[0] for r in rows]
    closes = [r[1] for r in rows]
    n = len(closes)
    ma = {w: [None] * n for w in windows}
    for w in windows:                       # O(n) rolling sum per window
        run = 0.0
        for i, c in enumerate(closes):
            run += c
            if i >= w:
                run -= closes[i - w]
            if i >= w - 1:
                ma[w][i] = run / w
    setcols = ", ".join(f"ma_{w}=?" for w in windows)
    db.executemany(
        f"UPDATE prices SET {setcols} WHERE instrument_id=? AND date=?",
        [tuple(ma[w][i] for w in windows) + (iid, dates[i]) for i in range(n)],
    )
    db.commit()
    return n


# ----------------------------------------------------------------------------
# Research papers — strategy literature that backs the Strategy Research log
# ----------------------------------------------------------------------------
def add_paper(db, title, authors=None, source=None, url=None, year=None,
              topic=None, strategy=None, summary=None, content=None,
              read_status="unread") -> int | None:
    """Add or update a research paper. Keyed on (title, source); idempotent upsert."""
    cur = db.execute(
        """
        INSERT INTO papers (title, authors, source, url, year, topic, strategy,
                            summary, content, read_status, added_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(title, source) DO UPDATE SET
            authors     = COALESCE(excluded.authors, papers.authors),
            url         = COALESCE(excluded.url, papers.url),
            year        = COALESCE(excluded.year, papers.year),
            topic       = COALESCE(excluded.topic, papers.topic),
            strategy    = COALESCE(excluded.strategy, papers.strategy),
            summary     = COALESCE(excluded.summary, papers.summary),
            content     = COALESCE(excluded.content, papers.content),
            read_status = excluded.read_status
        """,
        (title, authors, source, url, year, topic, strategy, summary, content, read_status, _now()),
    )
    db.commit()
    return cur.lastrowid


def get_papers(db, topic=None, strategy=None, unread_only=False):
    """List papers (newest first), optionally filtered by topic / strategy / unread."""
    q = ("SELECT title, authors, source, year, topic, strategy, read_status, url "
         "FROM papers WHERE 1=1")
    args = []
    if topic:
        q += " AND topic = ?"; args.append(topic)
    if strategy:
        q += " AND strategy = ?"; args.append(strategy)
    if unread_only:
        q += " AND read_status = 'unread'"
    q += " ORDER BY year DESC, title"
    return db.execute(q, args).fetchall()


# ----------------------------------------------------------------------------
# Watermark — lets daily runs pull only what's new
# ----------------------------------------------------------------------------
def set_last_fetched(db, company, when=None) -> None:
    cid = company_id(db, company)
    db.execute(
        "UPDATE instruments SET last_fetched = ? WHERE id = ?",
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
        for t in ("instruments", "industries", "news", "prices", "metrics", "filings")
    }
    print("Row counts:")
    for t, c in counts.items():
        print(f"  {t:<12} {c:,}")

    ac_rows = db.execute(
        "SELECT asset_class, COUNT(*) FROM instruments GROUP BY asset_class ORDER BY 2 DESC"
    ).fetchall()
    print("\nInstruments by asset_class:")
    for ac, n in ac_rows:
        print(f"  {ac:<12} {n}")

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
               (SELECT COUNT(*) FROM filings f WHERE f.company_id = c.id),
               c.last_fetched
        FROM instruments c
        ORDER BY c.name
        """
    ).fetchall()
    if rows:
        print("\nPer company (news / metrics / filings / industries / last_fetched):")
        for name, nnews, nmetrics, nfilings, lf in rows:
            inds = ", ".join(industries_of(db, name)) or "-"
            print(f"  {name:<20} {nnews:>4} / {nmetrics:>4} / {nfilings:>4}   {inds:<28} {lf or '-'}")


# ----------------------------------------------------------------------------
# Common-size statements (derived from the SEC/EDGAR dollar line items)
# ----------------------------------------------------------------------------
SEC_SOURCE = "SEC/EDGAR"

# statement -> (base line item, [line items expressed as a % of that base]).
# Only EDGAR statement line items; share counts are excluded (not $ amounts).
COMMON_SIZE_MAP = {
    "income":    ("revenue",      ["revenue", "operating_income", "net_income"]),
    "balance":   ("total_assets", ["total_assets", "total_liabilities", "total_equity",
                                   "current_assets", "current_liabilities"]),
    "cash_flow": ("revenue",      ["operating_cash_flow", "capital_expenditures",
                                   "free_cash_flow"]),
}


def recompute_common_size(db, company) -> int:
    """Rebuild common-size rows for one company from its SEC/EDGAR dollar metrics.

    Income & cash-flow items are stored as a fraction of revenue; balance-sheet items
    as a fraction of total assets. A (statement, period) is skipped when its base is
    missing or zero — you can't common-size without the denominator. Recomputes the
    whole set, so it's idempotent (safe to call after every EDGAR pull). Returns rows
    written."""
    cid = company_id(db, company, create=False)
    if cid is None:
        return 0
    rows = db.execute(
        "SELECT metric, period, value FROM metrics WHERE company_id=? AND source=?",
        (cid, SEC_SOURCE)).fetchall()
    by_mp = {(m, p): v for m, p, v in rows if v is not None}
    periods = {p for (_m, p) in by_mp}
    written = 0
    now = _now()
    for statement, (base_item, items) in COMMON_SIZE_MAP.items():
        for period in periods:
            base = by_mp.get((base_item, period))
            if not base:                        # missing or zero → can't divide
                continue
            for item in items:
                val = by_mp.get((item, period))
                if val is None:
                    continue
                db.execute(
                    """
                    INSERT INTO common_size
                        (company_id, statement, line_item, period, pct, base_item, computed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(company_id, statement, line_item, period) DO UPDATE SET
                        pct = excluded.pct, base_item = excluded.base_item,
                        computed_at = excluded.computed_at
                    """,
                    (cid, statement, item, period, val / base, base_item, now))
                written += 1
    db.commit()
    return written


def recompute_all_common_size(db):
    """Recompute common-size for every company that has SEC/EDGAR statements.
    Returns (companies, rows)."""
    cids = db.execute(
        "SELECT DISTINCT company_id FROM metrics WHERE source=?", (SEC_SOURCE,)).fetchall()
    companies = total = 0
    for (cid,) in cids:
        row = db.execute("SELECT name FROM instruments WHERE id=?", (cid,)).fetchone()
        if not row:
            continue
        n = recompute_common_size(db, row[0])
        if n:
            companies += 1
            total += n
    return companies, total


def get_common_size(db, company, statement=None, period=None):
    """Common-size rows [(statement, line_item, period, pct, base_item), ...] for a
    company, newest period first; optionally filtered by statement / period."""
    cid = company_id(db, company, create=False)
    if cid is None:
        return []
    q = ("SELECT statement, line_item, period, pct, base_item FROM common_size "
         "WHERE company_id=?")
    args = [cid]
    if statement:
        q += " AND statement=?"; args.append(statement)
    if period:
        q += " AND period=?"; args.append(period)
    q += " ORDER BY period DESC, statement, line_item"
    return db.execute(q, args).fetchall()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Finance database storage layer")
    ap.add_argument("--init", action="store_true", help="create the database schema")
    ap.add_argument("--load", metavar="JSON",
                    help="load a flat company list OR an industry-first mapping "
                         "(auto-detected)")
    ap.add_argument("--in-industry", metavar="NAME",
                    help="list the companies in an industry, then exit")
    ap.add_argument("--stats", action="store_true", help="show row counts")
    ap.add_argument("--recompute-common-size", dest="recompute_common_size",
                    action="store_true",
                    help="rebuild common-size statements for every company with EDGAR data")
    ap.add_argument("--show", metavar="URL",
                    help="print the full stored original text of a news item by URL")
    args = ap.parse_args()

    if not (args.init or args.load or args.in_industry or args.stats
            or args.recompute_common_size or args.show):
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
    if args.recompute_common_size:
        cos, rows = recompute_all_common_size(db)
        print(f"Common-size: {rows} rows across {cos} companies with EDGAR data.")
    if args.show:
        show_news(db, url=args.show)
