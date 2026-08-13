#!/usr/bin/env bash
# Install the global pre-commit hook for ALL repos on this machine, persistently.
#
# What it does:
#   1. copies the hook files into ~/.config/git/hooks/
#   2. points git at them GLOBALLY via  core.hooksPath  (applies to every repo,
#      existing and future)
#   3. also sets init.templateDir so freshly `git init`/`clone`d repos carry them
#
# Re-runnable (idempotent). Run once per machine:  bash tools/git-hooks/install.sh
set -eu

src="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dest="${XDG_CONFIG_HOME:-$HOME/.config}/git/hooks"
tmpl="${XDG_CONFIG_HOME:-$HOME/.config}/git/template"

mkdir -p "$dest" "$tmpl/hooks"
install -m 0755 "$src/pre-commit" "$dest/pre-commit"
install -m 0644 "$src/dupecheck.py" "$dest/dupecheck.py"
# keep a copy in the init template too (for new repos that override hooksPath)
install -m 0755 "$src/pre-commit" "$tmpl/hooks/pre-commit"
install -m 0644 "$src/dupecheck.py" "$tmpl/hooks/dupecheck.py"

git config --global core.hooksPath "$dest"
git config --global init.templateDir "$tmpl"

echo "✓ Installed global pre-commit hook."
echo "  core.hooksPath   = $(git config --global core.hooksPath)"
echo "  init.templateDir = $(git config --global init.templateDir)"
echo "  Applies to every repo. Bypass a single commit with: git commit --no-verify"
