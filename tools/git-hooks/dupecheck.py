#!/usr/bin/env python3
"""Warn on copy-pasted blocks in the staged Python files (stdlib only).

Heuristic: after stripping blank lines and comments, any run of >= WINDOW
identical, non-trivial normalized lines that appears in two places is reported.
Deliberately conservative (WINDOW=6, skips trivial lines) to keep false positives
low. Exit code 1 if any duplicate is found (the hook treats that as a warning
unless HOOK_STRICT_DUP=1), else 0.
"""
import sys
from collections import defaultdict

WINDOW = 6
# lines too trivial to count toward a "duplicated block"
TRIVIAL = {"", "else:", "try:", "return", "pass", "continue", "break", "})", ")", "]", "}"}


def normalized(path):
    """[(lineno, normalized_text), ...] keeping only substantive code lines."""
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for i, raw in enumerate(f, 1):
                s = raw.split("#", 1)[0].strip()      # drop trailing comments
                if s and s not in TRIVIAL and len(s) > 3:
                    out.append((i, s))
    except (OSError, UnicodeDecodeError):
        pass
    return out


def main(argv):
    seen = defaultdict(list)          # block signature -> [(file, start_line)]
    for path in argv:
        if not path.endswith(".py"):
            continue
        lines = normalized(path)
        for j in range(len(lines) - WINDOW + 1):
            window = lines[j:j + WINDOW]
            sig = "\n".join(t for _, t in window)
            seen[sig].append((path, window[0][0]))

    hits = {sig: locs for sig, locs in seen.items() if len(locs) > 1}
    if not hits:
        return 0
    print("  ⚠ duplicate code blocks (>= %d identical lines):" % WINDOW)
    for sig, locs in list(hits.items())[:10]:
        where = ", ".join(f"{p}:{ln}" for p, ln in locs)
        first = sig.splitlines()[0]
        print(f"    • {where}   e.g. “{first[:60]}”")
    print("  Consider extracting a shared helper (advisory; not blocking).")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
