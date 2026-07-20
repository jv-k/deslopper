#!/usr/bin/env bash
# Pre-bump gates for `pnpm bump-release`. Everything here has to pass before ver-bump runs.
# What ver-bump itself does is checked afterwards by postflight.sh, which runs before
# anything is pushed, so a bad bump is still local and cheap to undo.
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

# There used to be a check here that grepped `ver-bump --help` for a `--bump` flag, meaning
# to refuse a ver-bump that would bump package.json and leave pyproject.toml behind. It was
# checking an invalid invocation (the flag is -h), so it matched the error text instead of
# the help and refused every release, including correct ones. Whether the bump touched all
# three version files is a fact about the result, not about the help text, so postflight.sh
# asserts it after the bump instead.

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
