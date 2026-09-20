#!/usr/bin/env bash
# Pre-bump gates, run by VerBump as PRE_BUMP_CMD (see .verbumprc) after its own preflights
# and before it touches a file. What VerBump itself does is checked afterwards by
# postflight.sh, which runs before anything is pushed, so a bad bump is still local and
# cheap to undo.
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

# There used to be a check here that grepped `VerBump --help` for a `--bump` flag, meaning
# to refuse a VerBump that would bump package.json and leave pyproject.toml behind. It was
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

# The suite fakes the gateway, so this is the one place the live triage integration is
# exercised before a release. The fixture is excluded from the repo lint and is full of
# findings to judge. Exit 1 there means findings, which is the point; anything else is a
# usage or key error. A gateway failure keeps the scan's exit code by design, so the check
# that matters is that every finding came back judged.
if [ -z "${AI_GATEWAY_API_KEY:-}" ]; then
  echo "AI_GATEWAY_API_KEY is not set; the live triage smoke run needs it" >&2
  exit 1
fi
judged="$(mktemp)"
"$py" -m deslopper lint --triage --format json tests/fixtures/ai_slop.md >"$judged" || [ $? -eq 1 ]
"$py" - "$judged" <<'PY'
import json, sys
findings = json.load(open(sys.argv[1]))["findings"]
unjudged = [f for f in findings if "verdict" not in f]
if not findings or unjudged:
    sys.exit(f"triage smoke run: {len(unjudged)} of {len(findings)} findings came back unjudged")
print(f"triage smoke run: {len(findings)} findings judged")
PY
echo "preflight ok"
