#!/usr/bin/env python3
"""
migrate_schema.py — one-shot migration to the instrument-centric schema.

Transforms the legacy company-centric DB into:
  * companies            -> instruments  (+ asset_class, fund_strategy, currency, exchange)
  * asset_classes        NEW lookup table (seeded)
  * prices               NEW wide OHLCV time-series (replaces 5 EAV rows/day in metrics)
  * metrics              keeps ONLY sparse fundamentals; OHLCV pivoted out
  * company_industries   stays (now FK-references instruments)
  * companies            recreated as a VIEW for backward compatibility (read + write)

Idempotent-ish: refuses to run twice (detects `instruments` table).

    python migrate_schema.py finance.db
"""
import json
import sqlite3
import sys

OHLCV = ("price_open", "price_high", "price_low", "price_close", "volume")

ASSET_CLASSES = [
    ("stock",       "Individual company common stock / ADR"),
    ("etf",         "Exchange-traded fund"),
    ("fund",        "Closed-end / interval / mutual fund"),
    ("bond",        "Fixed income (bond fund or individual bond)"),
    ("reit",        "Real estate investment trust"),
    ("commodity",   "Commodity fund (gold, oil, ...)"),
    ("crypto",      "Crypto asset / spot crypto fund"),
    ("index",       "Index level (not directly tradable)"),
    ("cash",        "Cash / money-market / T-bill"),
]

# Explicit classification overrides by ticker (everything else => stock)
FUNDS   = {"DXYZ", "VCX"}                       # closed-end / interval pre-IPO funds
ACTIVE  = {"BLOK", "XOVR", "ARKQ", "DXYZ", "VCX"}  # actively managed


def classify(ticker: str, meta_json: str):
    """Return (asset_class, fund_strategy) for a legacy company row."""
    meta = json.loads(meta_json) if meta_json else {}
    is_etf = meta.get("type") == "etf"
    if ticker in FUNDS:
        return "fund", "active"
    if is_etf:
        return "etf", ("active" if ticker in ACTIVE else "index")
    return "stock", None


def migrate(path: str):
    db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys = ON")

    if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='instruments'").fetchone():
        print("Already migrated (instruments table exists). Aborting.")
        return

    # 1. add columns to companies
    for ddl in (
        "ALTER TABLE companies ADD COLUMN asset_class TEXT NOT NULL DEFAULT 'stock'",
        "ALTER TABLE companies ADD COLUMN fund_strategy TEXT",
        "ALTER TABLE companies ADD COLUMN currency TEXT DEFAULT 'USD'",
        "ALTER TABLE companies ADD COLUMN exchange TEXT",
    ):
        db.execute(ddl)

    # 2. classify each row
    rows = db.execute("SELECT id, ticker, meta FROM companies").fetchall()
    for cid, ticker, meta in rows:
        ac, fs = classify(ticker or "", meta)
        db.execute("UPDATE companies SET asset_class=?, fund_strategy=?, currency='USD' WHERE id=?",
                   (ac, fs, cid))
    db.commit()

    # 3. rename companies -> instruments (FK refs in child tables auto-rewrite while FK=ON)
    db.execute("ALTER TABLE companies RENAME TO instruments")

    # 4. asset_classes lookup
    db.execute("""CREATE TABLE asset_classes (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT)""")
    db.executemany("INSERT INTO asset_classes (name, description) VALUES (?, ?)", ASSET_CLASSES)

    # 5. prices wide table
    db.execute("""CREATE TABLE prices (
                    instrument_id INTEGER NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
                    date   TEXT NOT NULL,
                    open   REAL, high REAL, low REAL, close REAL, volume REAL,
                    source TEXT, fetched_at TEXT,
                    PRIMARY KEY (instrument_id, date))""")

    # 6. pivot OHLCV metrics -> prices
    db.execute("""
        INSERT INTO prices (instrument_id, date, open, high, low, close, volume, source, fetched_at)
        SELECT company_id, period,
               MAX(CASE WHEN metric='price_open'  THEN value END),
               MAX(CASE WHEN metric='price_high'  THEN value END),
               MAX(CASE WHEN metric='price_low'   THEN value END),
               MAX(CASE WHEN metric='price_close' THEN value END),
               MAX(CASE WHEN metric='volume'      THEN value END),
               MAX(source), MAX(fetched_at)
        FROM metrics
        WHERE metric IN ('price_open','price_high','price_low','price_close','volume')
        GROUP BY company_id, period
    """)
    moved = db.execute("SELECT COUNT(*) FROM prices").fetchone()[0]

    # 7. drop OHLCV rows from metrics (keep fundamentals)
    db.execute("DELETE FROM metrics WHERE metric IN ('price_open','price_high','price_low','price_close','volume')")

    # 8. indexes
    db.executescript("""
        CREATE INDEX IF NOT EXISTS idx_metrics_company_metric_period ON metrics(company_id, metric, period);
        CREATE INDEX IF NOT EXISTS idx_instruments_ticker      ON instruments(ticker);
        CREATE INDEX IF NOT EXISTS idx_instruments_asset_class ON instruments(asset_class);
        CREATE INDEX IF NOT EXISTS idx_prices_date             ON prices(date);
    """)

    # 9. backward-compat `companies` view + write-through triggers
    db.executescript("""
        CREATE VIEW companies AS
            SELECT id, name, ticker, sector, meta, summary, summary_updated_at,
                   last_fetched, created_at, asset_class, fund_strategy, currency, exchange
            FROM instruments;

        CREATE TRIGGER companies_ins INSTEAD OF INSERT ON companies BEGIN
            INSERT OR IGNORE INTO instruments (name, ticker, sector, meta, summary,
                   summary_updated_at, last_fetched, created_at)
            VALUES (NEW.name, NEW.ticker, NEW.sector, NEW.meta, NEW.summary,
                   NEW.summary_updated_at, NEW.last_fetched, NEW.created_at);
        END;

        CREATE TRIGGER companies_upd INSTEAD OF UPDATE ON companies BEGIN
            UPDATE instruments SET name=NEW.name, ticker=NEW.ticker, sector=NEW.sector,
                   meta=NEW.meta, summary=NEW.summary, summary_updated_at=NEW.summary_updated_at,
                   last_fetched=NEW.last_fetched WHERE id=OLD.id;
        END;

        CREATE TRIGGER companies_del INSTEAD OF DELETE ON companies BEGIN
            DELETE FROM instruments WHERE id=OLD.id;
        END;
    """)

    db.commit()

    # 10. reclaim space
    db.execute("VACUUM")
    db.commit()

    remaining = db.execute("SELECT COUNT(*) FROM metrics").fetchone()[0]
    ac_counts = db.execute("SELECT asset_class, COUNT(*) FROM instruments GROUP BY asset_class ORDER BY 2 DESC").fetchall()
    print(f"OK. Pivoted {moved:,} price rows into `prices`.")
    print(f"metrics now holds {remaining:,} rows (fundamentals only).")
    print("Instruments by asset_class:", dict(ac_counts))
    db.close()


if __name__ == "__main__":
    migrate(sys.argv[1] if len(sys.argv) > 1 else "finance.db")
