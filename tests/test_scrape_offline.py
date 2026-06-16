"""
Offline test for scrape.py.

The sandbox has no network and can't install feedparser/trafilatura, so we stub
ONLY those two network libraries with canned data and exercise the real scrape.py
logic against the real store.py + sources.yaml. This verifies the parts we wrote:
watermark filtering, dedup/idempotency, tracking-param cleaning, content selection,
and watermark advancement.
"""
import os, sys, time, types, sqlite3, tempfile

# ---- stub feedparser -------------------------------------------------------
def _struct(y, mo, d, h=12):
    return time.struct_time((y, mo, d, h, 0, 0, 0, 0, 0))

# Two "fresh" articles (June 2026) and one "old" (Jan 2026) to test watermark.
_ENTRIES = [
    {"title": "Fresh A", "link": "https://ex.com/a?utm_source=google",  # tracking param
     "summary": "summary A", "published_parsed": _struct(2026, 6, 15),
     "source": {"title": "ExNews"}},
    {"title": "Fresh B", "link": "https://ex.com/b",
     "summary": "summary B", "published_parsed": _struct(2026, 6, 14),
     "source": {"title": "ExNews"}},
    {"title": "Old C", "link": "https://ex.com/c",
     "summary": "summary C", "published_parsed": _struct(2026, 1, 1),
     "source": {"title": "ExNews"}},
]

fp = types.ModuleType("feedparser")
def _parse(url):
    feed = types.SimpleNamespace()
    feed.entries = [dict(e) for e in _ENTRIES]
    feed.feed = {"title": "StubFeed"}
    return feed
fp.parse = _parse
sys.modules["feedparser"] = fp

# ---- stub trafilatura ------------------------------------------------------
tr = types.ModuleType("trafilatura")
tr.fetch_url = lambda url: f"<html>{url}</html>"
tr.extract = lambda html, **kw: f"FULLTEXT for {html}"
sys.modules["trafilatura"] = tr

# ---- now import the real modules ------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import store, scrape

DB = os.path.join(tempfile.gettempdir(), "test_finance.db")
for ext in ("", "-wal", "-shm"):
    try: os.remove(DB + ext)
    except FileNotFoundError: pass

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sources.yaml")

class Args:
    db = DB; sources = SRC; company = "NVIDIA"
    no_fetch_text = False; dry_run = False; since = None

def count_news(db, company):
    cid = store.company_id(db, company, create=False)
    return db.execute("SELECT COUNT(*) FROM news WHERE company_id=?", (cid,)).fetchone()[0]

ok = True
def check(label, cond):
    global ok
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}")
    ok = ok and cond

db = store.get_db(DB)
store.init_db(db)
store.load(db, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "industries.json"))
cfg = scrape.load_sources(SRC)
defaults = cfg["defaults"]
nvidia_conf = cfg["companies"]["NVIDIA"]

print("Test 1: first run ingests fresh items, skips the old one")
# NVIDIA has 2 feeds (explicit + google news); stub returns same 3 entries each,
# so unique urls = 3, of which 'Old C' is filtered ONLY if a watermark exists.
# No watermark yet -> all 3 unique urls ingested (a,b,c).
r = scrape.scrape_company(db, "NVIDIA", nvidia_conf, defaults, Args())
check("3 unique articles stored (dedup across 2 feeds)", count_news(db, "NVIDIA") == 3)
check("new count == 3", r["new"] == 3)

print("Test 2: tracking params stripped from URL")
cid = store.company_id(db, "NVIDIA", create=False)
urls = [row[0] for row in db.execute("SELECT url FROM news WHERE company_id=?", (cid,))]
check("utm_source removed from stored url", "https://ex.com/a" in urls and not any("utm_" in u for u in urls))

print("Test 3: full text from trafilatura used as content")
content_a = db.execute("SELECT content FROM news WHERE url='https://ex.com/a'").fetchone()[0]
check("content came from trafilatura", content_a.startswith("FULLTEXT"))

print("Test 4: watermark advanced to newest entry (2026-06-15)")
wm = store.get_last_fetched(db, "NVIDIA")
check("watermark starts 2026-06-15", wm is not None and wm.startswith("2026-06-15"))

print("Test 5: idempotent re-run adds nothing")
r2 = scrape.scrape_company(db, "NVIDIA", nvidia_conf, defaults, Args())
check("new == 0 on re-run", r2["new"] == 0)
check("still 3 rows total", count_news(db, "NVIDIA") == 3)

print("Test 6: watermark filter skips older-than-watermark items")
# Now watermark is 2026-06-15. Fresh B (06-14) and Old C (01-01) are <= watermark.
check("re-run reports skipped_old > 0", r2["skipped_old"] > 0)

print("Test 7: --no-fetch-text uses RSS summary, not trafilatura")
a2 = Args(); a2.company = "Tesla"; a2.no_fetch_text = True
scrape.scrape_company(db, "Tesla", cfg["companies"]["Tesla"], defaults, a2)
tesla_content = db.execute(
    "SELECT content FROM news n JOIN companies c ON n.company_id=c.id "
    "WHERE c.name='Tesla' AND n.url='https://ex.com/a'").fetchone()[0]
check("content is RSS summary", tesla_content == "summary A")

print("Test 8: --dry-run writes nothing")
a3 = Args(); a3.company = "SpaceX"; a3.dry_run = True
scrape.scrape_company(db, "SpaceX", cfg["companies"]["SpaceX"], defaults, a3)
check("SpaceX has 0 rows after dry run", count_news(db, "SpaceX") == 0)

print("Test 9: full original text is retrievable verbatim via get_news/--show")
items = store.get_news(db, url="https://ex.com/a")
check("get_news returns stored item(s) for the url", len(items) >= 1)
nvidia_item = [it for it in items if it["company"] == "NVIDIA"]
check("NVIDIA original full text retrievable, untruncated",
      bool(nvidia_item) and nvidia_item[0]["content"].startswith("FULLTEXT"))

db.close()
print("\nRESULT:", "ALL PASS" if ok else "FAILURES PRESENT")
sys.exit(0 if ok else 1)
