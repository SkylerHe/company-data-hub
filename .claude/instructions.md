# MarketHub - AI Agent Guidelines

## 🔒 Security & Privacy (CRITICAL)

**NEVER commit or push:**
- API keys (Finnhub, any future APIs)
- Email addresses (SEC_IDENTITY)
- Personal information
- Environment variables with sensitive data

**Always check:**
- `.env` file is in `.gitignore`
- No hardcoded credentials in code
- Use environment variables for all secrets

---

## ✅ Code Quality Standards

### 1. Always Test Functions
- Test every new function before marking task complete
- Run manual tests with real data when possible
- Verify error handling works correctly
- Example: `python scrape_yahoo.py --company NVIDIA` (test single company first)

### 2. Check for Unused Code
Before completing any task, scan for:
- Unused imports
- Dead functions (defined but never called)
- Commented-out code blocks
- Old configuration files from removed features

**Commands to check:**
```bash
# Find unused imports (manually review each file)
grep "^import\|^from" *.py

# Search for function definitions and verify they're used
grep "^def " *.py
```

### 3. Check for Duplicate Code
- Look for repeated logic across scrapers
- Extract common patterns to `store.py` or helper functions
- DRY principle: Don't Repeat Yourself

### 4. Check Test Functions
- Remove test files when removing features (like we did with `tests/` for old scraper)
- If adding tests, ensure they run in CI/CD
- Keep tests minimal and focused on this personal project

---

## 📋 Project-Specific Rules

### Data Collection
- **Yahoo Finance**: Bi-weekly updates (fundamentals change quarterly)
- **IBKR Prices**: Daily updates (when IB Gateway running)
- **SEC Filings**: Weekly updates
- **Finnhub News**: 3x per week (optional)

### Update Frequency Rationale
- Don't waste API calls on data that doesn't change
- Fundamentals only update with quarterly earnings
- Balance freshness vs. efficiency

### Code Organization
```
scrape_*.py     → Data collection scripts (one per source)
store.py        → Database operations only
update.py       → Smart update orchestration
dashboard.py    → Web UI for viewing data
```

### When Making Changes
1. Test the specific function/script
2. Check for unused code from the change
3. Update README.md if user-facing behavior changes
4. Update SUMMARY.md if data structure changes
5. Never create new files unless absolutely necessary

---

## 🎯 User's Learning Goals

**Primary goal:** Learn value/growth investing + CFA Level 1 prep + practice trading with $100-1000

**Data priorities:**
1. Fundamental analysis (P/E, ROE, margins, debt ratios)
2. Price history for technical analysis
3. SEC filings for deep research
4. News for staying informed

**Keep it simple:** This is a personal learning project, not enterprise software. Optimize for learning, not scale.

---

## 🧹 Cleanup Checklist (Run Periodically)

```bash
# 1. Check for test files
find . -name "*test*.py" -o -name "*Test*.py" | grep -v venv

# 2. Check for unused scripts
ls *.sh *.py | xargs -I {} echo "Check if {} is referenced in README/SUMMARY"

# 3. Check database size
du -sh finance.db

# 4. Verify .gitignore is protecting secrets
cat .gitignore
```

---

## 💡 Development Workflow

**When adding features:**
1. Plan → Test → Implement → Test again → Update docs
2. Always prefer editing existing files over creating new ones
3. Remove old code when replacing functionality
4. Keep the project lean (we removed Docker, tests/, shell scripts already)

**When fixing bugs:**
1. Reproduce the issue first
2. Fix in smallest possible change
3. Test the fix
4. Look for similar issues elsewhere

---

_Last updated: 2026-07-02_
_This file serves as persistent memory for AI agents working on this project._
