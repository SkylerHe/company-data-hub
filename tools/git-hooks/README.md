# Global git hooks

A pre-commit hook that enforces the two house rules on **every repo on the
machine** (not just this one):

- **Dead code → blocks the commit.** Runs `ruff` (fallback `flake8`) on staged
  `*.py` files for unused imports/variables, redefinitions, and undefined names
  (`F401,F811,F841,F823`).
- **Duplicate blocks → warns.** `dupecheck.py` flags ≥6 identical non-trivial
  lines appearing in two places. Advisory by default; set `HOOK_STRICT_DUP=1` to
  make it blocking too.

## Install (once per machine — persistent)

```bash
bash tools/git-hooks/install.sh
```

This copies the hook into `~/.config/git/hooks/`, sets `core.hooksPath` globally
(so it applies to every existing and future repo), and sets `init.templateDir`
so newly `git init`/`clone`d repos carry it as well.

## Notes

- Requires `ruff` (preferred) or `flake8` on PATH or importable; with neither, the
  dead-code gate is skipped with a printed notice rather than failing.
- Bypass a single commit: `git commit --no-verify`.
- The files live in-repo so they're version-controlled; re-run `install.sh` on any
  new machine to get the same enforcement everywhere.
