#!/usr/bin/env bash
# Pre-tag gates for `pnpm bump-release`. Everything here has to pass before ver-bump
# bumps, commits, tags and pushes, so a failure lands while it is still cheap: once the
# tag is public, release.yml can only fail loudly and the tag has to be deleted and re-cut.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -n "$(git status --porcelain)" ]; then
  echo "working tree is not clean; commit or stash first" >&2
  exit 1
fi

branch="$(git symbolic-ref --quiet --short HEAD || true)"
if [ "$branch" != "main" ]; then
  echo "on ${branch:-a detached HEAD}; releases are cut from main" >&2
  exit 1
fi

# A ver-bump without --bump targets does not fail on .ver-bumprc's BUMP_FILES. It ignores
# them and reports success, bumping package.json and leaving pyproject.toml behind, which
# is how v0.1.2 shipped broken. The gates cannot catch that afterwards: ver-bump tags and
# pushes in the same run. So refuse the tool before it starts.
# Captured, not piped into grep -q: grep exits on the first match and closes the pipe,
# ver-bump takes SIGPIPE, and pipefail then reads the whole check as a failure, which
# refuses every ver-bump including the right one.
ver_bump_help="$(ver-bump --help 2>&1 || true)"
case "$ver_bump_help" in
  *--bump*) ;;
  *)
    echo "this ver-bump has no --bump targets: it would bump package.json alone and leave" >&2
    echo "pyproject.toml behind. See RELEASING.md." >&2
    exit 1
    ;;
esac

py=.venv/bin/python
if [ ! -x "$py" ] || ! "$py" -c 'import pytest, deslopper, build' >/dev/null 2>&1; then
  echo "need a .venv with deslopper, pytest, and build installed:" >&2
  echo "  python3 -m venv .venv && .venv/bin/pip install -e . pytest build" >&2
  exit 1
fi

"$py" -m pytest -q
"$py" -m deslopper lint
"$py" -m build --outdir "$(mktemp -d)" >/dev/null
echo "preflight ok"
