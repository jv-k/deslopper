#!/usr/bin/env bash
# Bump the version, retitle the changelog, commit, and release, in one step.
# Usage: pnpm bump-release [patch|minor|major]   (default: patch)
# CHANGELOG.md must already have an `(unreleased)` section listing the changes; the
# script retitles it to the new version. scripts/release.sh runs the gates and pushes.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -n "$(git status --porcelain)" ]; then
  echo "working tree is not clean; commit or stash first" >&2
  exit 1
fi

if ! grep -qE '^## .*\(unreleased\)' CHANGELOG.md; then
  echo "CHANGELOG.md has no '(unreleased)' section; add the entries first" >&2
  exit 1
fi

new="$(python3 scripts/bump.py "${1:-patch}")"

python3 - "$new" <<'PYEOF'
import pathlib
import re
import sys

new = sys.argv[1]
path = pathlib.Path("CHANGELOG.md")
text = path.read_text(encoding="utf-8")
path.write_text(
    re.sub(r"^## .*\(unreleased\)\s*$", f"## {new}", text, count=1, flags=re.M),
    encoding="utf-8",
)
PYEOF

git add pyproject.toml src/deslopper/__init__.py package.json CHANGELOG.md
git commit -m "chore(release): v$new"
exec bash scripts/release.sh
