"""Offline test for the industry features in store.py + scrape.py."""
import os, sys, types, tempfile

# stub the two network libs so importing scrape works offline
fp = types.ModuleType("feedparser"); fp.parse = lambda u: types.SimpleNamespace(entries=[], feed={})
sys.modules["feedparser"] = fp
tr = types.ModuleType("trafilatura"); tr.fetch_url = lambda u: None; tr.extract = lambda *a, **k: None
sys.modules["trafilatura"] = tr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import store, scrape

DB = os.path.join(tempfile.gettempdir(), "test_ind.db")
for ext in ("", "-wal", "-shm"):
    try: os.remove(DB + ext)
    except FileNotFoundError: pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ok = True
def check(label, cond):
    global ok; print(f"  [{'PASS' if cond else 'FAIL'}] {label}"); ok = ok and cond

db = store.get_db(DB); store.init_db(db)

print("Test 1: industry-first load (auto-detected as dict)")
store.load(db, os.path.join(HERE, "industries.json"))
check("5 industries loaded", db.execute("SELECT COUNT(*) FROM industries").fetchone()[0] == 5)
check("4 distinct companies", db.execute("SELECT COUNT(*) FROM companies").fetchone()[0] == 4)

print("Test 2: multi-membership")
check("NVIDIA in Semiconductors + AI",
      set(store.industries_of(db, "NVIDIA")) == {"Semiconductors", "Artificial Intelligence"})
check("Tesla in Automotive + Energy + AI",
      set(store.industries_of(db, "Tesla")) == {"Automotive", "Energy", "Artificial Intelligence"})

print("Test 3: companies_in_industry (the search primitive)")
check("Semiconductors -> NVIDIA + TSM",
      store.companies_in_industry(db, "Semiconductors") == ["NVIDIA", "Taiwan Semiconductor"])
check("AI -> NVIDIA + Tesla",
      set(store.companies_in_industry(db, "Artificial Intelligence")) == {"NVIDIA", "Tesla"})
check("unknown industry -> []", store.companies_in_industry(db, "Nope") == [])

print("Test 4: ticker preserved through industry-first load")
check("NVDA ticker stored",
      db.execute("SELECT ticker FROM companies WHERE name='NVIDIA'").fetchone()[0] == "NVDA")

print("Test 5: idempotent reload (no dup industries, companies, or links)")
store.load(db, os.path.join(HERE, "industries.json"))
check("still 5 industries", db.execute("SELECT COUNT(*) FROM industries").fetchone()[0] == 5)
check("still 4 companies", db.execute("SELECT COUNT(*) FROM companies").fetchone()[0] == 4)
check("NVIDIA still 2 links", len(store.industries_of(db, "NVIDIA")) == 2)

print("Test 6: industry-level feeds reach member companies (feeds_for)")
defaults = {"google_news": False, "language": "en-US", "country": "US"}
ind_feeds = {"Semiconductors": ["https://chipfeed.example/rss"]}
feeds = scrape.feeds_for("NVIDIA", {"feeds": ["https://nvidia.example/ir"]},
                         defaults, ind_feeds, store.industries_of(db, "NVIDIA"))
check("NVIDIA gets its own feed + the Semiconductors industry feed",
      feeds == ["https://nvidia.example/ir", "https://chipfeed.example/rss"])
feeds_tesla = scrape.feeds_for("Tesla", {}, defaults, ind_feeds, store.industries_of(db, "Tesla"))
check("Tesla (not a chip co) does NOT get the Semiconductors feed",
      "https://chipfeed.example/rss" not in feeds_tesla)

print("Test 7: feeds_for dedups + adds Google News when enabled")
d2 = {"google_news": True, "language": "en-US", "country": "US"}
feeds = scrape.feeds_for("NVIDIA", {"feeds": ["https://x/rss", "https://x/rss"]},
                         d2, {}, [])
check("duplicate feed collapsed", feeds.count("https://x/rss") == 1)
check("google news appended", any("news.google.com" in f for f in feeds))

db.close()
print("\nRESULT:", "ALL PASS" if ok else "FAILURES PRESENT")
sys.exit(0 if ok else 1)
