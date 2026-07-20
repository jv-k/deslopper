#!/usr/bin/env bash
# Post-bump gates for `pnpm bump-release`. These run after ver-bump has bumped, committed
# and tagged, and before anything is pushed, so a bad bump is caught while the tag is still
# local. Recovery is then `git reset --hard HEAD~1 && git tag -d vX.Y.Z`, as RELEASING.md
# describes. Once a tag is public it has to be deleted on the remote and re-cut.
set -euo pipefail
cd "$(dirname "$0")/.."

py=.venv/bin/python
if [ ! -x "$py" ]; then
  echo "need a .venv; see preflight.sh" >&2
  exit 1
fi

version="$("$py" -c 'import json; print(json.load(open("package.json"))["version"])')"

# ver-bump commits its own changes. Anything left behind means the bump did not finish.
if [ -n "$(git status --porcelain)" ]; then
  echo "working tree is not clean after the bump; ver-bump left changes uncommitted" >&2
  exit 1
fi

tag="$(git describe --exact-match --tags HEAD 2>/dev/null || true)"
if [ "$tag" != "v$version" ]; then
  echo "HEAD is tagged '${tag:-nothing}', expected 'v$version'" >&2
  exit 1
fi

# The version lives in three files and they have to agree. A ver-bump that only knows
# package.json leaves pyproject.toml and __init__.py behind, which is how v0.1.2 broke.
"$py" -m pytest -q tests/test_version.py

# Without -c, ver-bump rewrites CHANGELOG.md with raw commit subjects. Those land above the
# title and carry the em dashes this repo's own linter rejects, which is how v0.2.0 shipped
# a red main. Lint here, while the tag is still local.
"$py" -m deslopper lint

"$py" -m pytest -q

echo "postflight ok: v$version is ready to push"
