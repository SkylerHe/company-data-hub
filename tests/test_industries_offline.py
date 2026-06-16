"""Offline test for the industry features in store.py + scrape.py.

Assertions are derived from industries.json itself (not hard-coded counts), so the
test stays correct as the tracked universe of industries/companies grows."""
import os, sys, json, types, tempfile, collections

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
IND_FILE = os.path.join(HERE, "industries.json")

# ---- expected truth, computed straight from the data file ------------------
raw = json.load(open(IND_FILE))
expected_industries = set(raw.keys())
members = {ind: [ (c if isinstance(c, str) else c["name"]) for c in body["companies"] ]
           for ind, body in raw.items()}
all_companies = set()
membership = collections.defaultdict(set)   # company -> {industries}
for ind, names in members.items():
    for nm in names:
        all_companies.add(nm)
        membership[nm].add(ind)

ok = True
def check(label, cond):
    global ok; print(f"  [{'PASS' if cond else 'FAIL'}] {label}"); ok = ok and cond

db = store.get_db(DB); store.init_db(db)

print("Test 1: industry-first load (auto-detected as dict)")
store.load(db, IND_FILE)
n_ind = db.execute("SELECT COUNT(*) FROM industries").fetchone()[0]
n_co = db.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
check(f"{len(expected_industries)} industries loaded", n_ind == len(expected_industries))
check(f"{len(all_companies)} distinct companies", n_co == len(all_companies))

print("Test 2: multi-membership matches the file")
# pick the company that appears in the most industries as the multi-membership probe
multi = max(membership, key=lambda c: len(membership[c]))
check(f"{multi} is in >1 industry (probe is meaningful)", len(membership[multi]) > 1)
check(f"{multi} industries match the file",
      set(store.industries_of(db, multi)) == membership[multi])

print("Test 3: companies_in_industry (the search primitive)")
probe_ind = "Semiconductors"
check(f"{probe_ind} membership matches the file",
      set(store.companies_in_industry(db, probe_ind)) == set(members[probe_ind]))
check("results are sorted", store.companies_in_industry(db, probe_ind) ==
      sorted(store.companies_in_industry(db, probe_ind)))
check("unknown industry -> []", store.companies_in_industry(db, "Nope") == [])

print("Test 4: ticker preserved through industry-first load")
check("NVDA ticker stored",
      db.execute("SELECT ticker FROM companies WHERE name='NVIDIA'").fetchone()[0] == "NVDA")

print("Test 5: idempotent reload (no dup industries, companies, or links)")
links_before = len(store.industries_of(db, multi))
store.load(db, IND_FILE)
check("industry count unchanged",
      db.execute("SELECT COUNT(*) FROM industries").fetchone()[0] == len(expected_industries))
check("company count unchanged",
      db.execute("SELECT COUNT(*) FROM companies").fetchone()[0] == len(all_companies))
check(f"{multi} link count unchanged", len(store.industries_of(db, multi)) == links_before)

print("Test 6: industry-level feeds reach member companies (feeds_for)")
defaults = {"google_news": False, "language": "en-US", "country": "US"}
ind_feeds = {"Semiconductors": ["https://chipfeed.example/rss"]}
feeds = scrape.feeds_for("NVIDIA", {"feeds": ["https://nvidia.example/ir"]},
                         defaults, ind_feeds, store.industries_of(db, "NVIDIA"))
check("NVIDIA gets its own feed + the Semiconductors industry feed",
      "https://nvidia.example/ir" in feeds and "https://chipfeed.example/rss" in feeds)
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
