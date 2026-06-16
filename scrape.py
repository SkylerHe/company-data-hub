"""
scrape.py — the daily news scraper for the company finance database.

What it does, per company in sources.yaml:
  1. Reads its feeds (explicit RSS/Atom feeds + an auto-built Google News feed).
  2. Filters entries newer than the company's `last_fetched` watermark, so daily
     runs only do work on new items. (Re-running is safe regardless: store.py
     dedupes by company+url, so nothing is ever duplicated.)
  3. Optionally pulls the full article text with trafilatura.
  4. Writes each item via store.add_news(...), then advances the watermark.

It is deliberately resilient: a bad feed or a single unreachable article never
aborts the run. Everything lives in store.py's schema; this file only ingests.

    pip install -r requirements.txt
    python store.py --init                     # once, creates finance.db
    python store.py --load industries.json     # once, loads your industries + companies
    python scrape.py                           # the daily job

Useful flags:
    python scrape.py --company NVIDIA          # only one company
    python scrape.py --no-fetch-text           # title + RSS summary only (fast)
    python scrape.py --dry-run                 # fetch + parse, write nothing
    python scrape.py --since 2026-06-01        # override watermark for a backfill
    python scrape.py --db finance.db --sources sources.yaml
"""

import argparse
import sys
import time
import urllib.parse
from datetime import datetime, timezone

import feedparser
import yaml

import store

# trafilatura is only needed when we fetch full text; import lazily so
# --no-fetch-text works even if it isn't installed.
try:
    import trafilatura
except Exception:  # pragma: no cover
    trafilatura = None


# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
def load_sources(path: str) -> dict:
    with open(path) as f:
        cfg = yaml.safe_load(f) or {}
    cfg.setdefault("defaults", {})
    cfg.setdefault("companies", {})
    cfg.setdefault("industries", {})
    d = cfg["defaults"]
    d.setdefault("google_news", True)
    d.setdefault("language", "en-US")
    d.setdefault("country", "US")
    d.setdefault("max_articles_per_feed", 25)
    d.setdefault("fetch_full_text", True)
    return cfg


def google_news_url(query: str, language: str, country: str) -> str:
    """Build a Google News RSS search URL for a query string."""
    q = urllib.parse.quote(query)
    ceid = f"{country}:{language.split('-')[0]}"
    return (
        f"https://news.google.com/rss/search?q={q}"
        f"&hl={language}&gl={country}&ceid={ceid}"
    )


def feeds_for(company, conf, defaults, industry_feeds=None, company_industries=None):
    """All feed URLs to read for a company:
        explicit company feeds + industry feeds (for its industries) + Google News.
    Deduped, order preserved.
    """
    conf = conf or {}
    feeds = list(conf.get("feeds") or [])

    # Industry-level feeds, applied to every member company.
    for ind in (company_industries or []):
        feeds.extend((industry_feeds or {}).get(ind, []))

    use_gn = conf.get("google_news", defaults["google_news"])
    if use_gn:
        query = conf.get("query") or f'"{company}"'
        feeds.append(
            google_news_url(query, defaults["language"], defaults["country"])
        )
    # Dedup while preserving order.
    seen, out = set(), []
    for f in feeds:
        if f and f not in seen:
            seen.add(f)
            out.append(f)
    return out


# ----------------------------------------------------------------------------
# Parsing helpers
# ----------------------------------------------------------------------------
def entry_datetime(entry) -> datetime | None:
    """Best-effort published datetime (UTC) from a feed entry."""
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            try:
                return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)
            except (TypeError, ValueError, OverflowError):
                continue
    return None


def parse_iso(s: str) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def clean_url(url: str) -> str:
    """Strip tracking query params so the same article dedupes reliably."""
    if not url:
        return url
    try:
        parts = urllib.parse.urlsplit(url)
        keep = [
            (k, v)
            for k, v in urllib.parse.parse_qsl(parts.query)
            if not k.lower().startswith(("utm_", "gclid", "fbclid", "oc"))
        ]
        return urllib.parse.urlunsplit(
            (parts.scheme, parts.netloc, parts.path,
             urllib.parse.urlencode(keep), "")
        )
    except Exception:
        return url


def fetch_full_text(url: str) -> str | None:
    """Download a page and return its FULL article text (plain text, not HTML).

    This complete text is what gets stored verbatim in news.content, so the
    original can always be shown again later — no summarizing, no truncation."""
    if trafilatura is None:
        return None
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        return trafilatura.extract(
            downloaded, include_comments=False, include_tables=False
        )
    except Exception:
        return None


# ----------------------------------------------------------------------------
# Core
# ----------------------------------------------------------------------------
def scrape_company(db, company, conf, defaults, args, industry_feeds=None) -> dict:
    """Scrape one company. Returns a small summary dict for reporting."""
    result = {"seen": 0, "new": 0, "skipped_old": 0, "errors": 0}

    # Watermark: only consider entries newer than this.
    if args.since:
        watermark = parse_iso(args.since)
    else:
        watermark = parse_iso(store.get_last_fetched(db, company))

    newest_seen = watermark
    company_industries = store.industries_of(db, company)
    feeds = feeds_for(company, conf, defaults, industry_feeds, company_industries)
    fetch_text = defaults["fetch_full_text"] and not args.no_fetch_text
    cap = defaults["max_articles_per_feed"]

    for feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"    ! feed error ({feed_url[:60]}...): {e}")
            result["errors"] += 1
            continue

        for entry in parsed.entries[:cap]:
            result["seen"] += 1
            dt = entry_datetime(entry)

            # Watermark filter (only when we have a date to compare).
            if watermark and dt and dt <= watermark:
                result["skipped_old"] += 1
                continue
            if dt and (newest_seen is None or dt > newest_seen):
                newest_seen = dt

            url = clean_url(entry.get("link", ""))
            if not url:
                continue
            title = entry.get("title", "(untitled)")
            source = entry.get("source", {}).get("title") or parsed.feed.get("title", "")
            published_at = dt.date().isoformat() if dt else None

            content = entry.get("summary", "")
            if fetch_text:
                full = fetch_full_text(url)
                if full:
                    content = full

            if args.dry_run:
                result["new"] += 1
                continue

            try:
                new_id = store.add_news(
                    db, company, source, url, title, published_at, content
                )
                if new_id is not None:
                    result["new"] += 1
            except Exception as e:
                print(f"    ! store error: {e}")
                result["errors"] += 1

    # Advance the watermark to the newest item we actually saw (or now).
    if not args.dry_run:
        stamp = (newest_seen or datetime.now(timezone.utc)).isoformat(timespec="seconds")
        store.set_last_fetched(db, company, stamp)

    return result


def main():
    ap = argparse.ArgumentParser(description="Daily news scraper")
    ap.add_argument("--db", default=store.DB_PATH, help="SQLite path")
    ap.add_argument("--sources", default="sources.yaml", help="feed config")
    ap.add_argument("--company", help="limit to one company (by name)")
    ap.add_argument("--no-fetch-text", action="store_true",
                    help="skip full-text fetch; use RSS summaries")
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch and parse but write nothing")
    ap.add_argument("--since", help="override watermark, ISO date (e.g. 2026-06-01)")
    args = ap.parse_args()

    cfg = load_sources(args.sources)
    defaults = cfg["defaults"]
    companies = cfg["companies"]
    industry_feeds = {
        name: (body or {}).get("feeds") or []
        for name, body in cfg["industries"].items()
    }

    if args.company:
        if args.company not in companies:
            print(f"'{args.company}' not in {args.sources}", file=sys.stderr)
            sys.exit(1)
        companies = {args.company: companies[args.company]}

    db = store.get_db(args.db)
    store.init_db(db)  # safe; no-op if it already exists

    totals = {"seen": 0, "new": 0, "skipped_old": 0, "errors": 0}
    print(f"Scraping {len(companies)} company(ies) "
          f"{'(dry run) ' if args.dry_run else ''}from {args.sources}\n")

    for company, conf in companies.items():
        print(f"  {company}")
        r = scrape_company(db, company, conf, defaults, args, industry_feeds)
        print(f"    seen={r['seen']} new={r['new']} "
              f"skipped_old={r['skipped_old']} errors={r['errors']}")
        for k in totals:
            totals[k] += r[k]

    print(f"\nDone. new={totals['new']} seen={totals['seen']} "
          f"skipped_old={totals['skipped_old']} errors={totals['errors']}")
    db.close()


if __name__ == "__main__":
    main()
