#!/usr/bin/env bash
# Tag and push a deslopper release from main. Bump the version and commit it first (see
# RELEASING.md). Runs the pre-tag gates (version check, tests, lint, build) so a failure
# surfaces before the tag exists, then pushes main and the tag in one atomic push. The
# pushed tag triggers .github/workflows/release.yml, which rebuilds and publishes to PyPI.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -n "$(git status --porcelain)" ]; then
  echo "working tree is not clean; commit the version bump first" >&2
  exit 1
fi

branch="$(git symbolic-ref --quiet --short HEAD || true)"
if [ "$branch" != "main" ]; then
  echo "on ${branch:-a detached HEAD}; releases are cut from main" >&2
  exit 1
fi

py=.venv/bin/python
if [ ! -x "$py" ] || ! "$py" -c 'import pytest, deslopper, build' >/dev/null 2>&1; then
  echo "need a .venv with deslopper, pytest, and build installed:" >&2
  echo "  python3 -m venv .venv && .venv/bin/pip install -e . pytest build" >&2
  exit 1
fi

version="$(grep -Em1 '^version = "[0-9]+\.[0-9]+\.[0-9]+"$' pyproject.toml | sed -E 's/.*"(.*)".*/\1/')"
if [ -z "$version" ]; then
  echo "could not read an X.Y.Z version from pyproject.toml" >&2
  exit 1
fi

module_version="$("$py" -c 'import deslopper; print(deslopper.__version__)')"
if [ "$module_version" != "$version" ]; then
  echo "pyproject.toml has $version but deslopper.__version__ is $module_version; run scripts/bump.py" >&2
  exit 1
fi

tag="v$version"
if git rev-parse "$tag" >/dev/null 2>&1; then
  echo "tag $tag already exists locally" >&2
  exit 1
fi
if git ls-remote --exit-code origin "refs/tags/$tag" >/dev/null 2>&1; then
  echo "tag $tag already exists on origin" >&2
  exit 1
fi

"$py" -m pytest -q
"$py" -m deslopper lint
"$py" -m build --outdir "$(mktemp -d)"

echo "Releasing $tag"
git tag "$tag"
if ! git push --atomic origin refs/heads/main "refs/tags/$tag"; then
  git tag -d "$tag" >/dev/null
  echo "push failed; nothing was released and the local tag was removed. Fix and rerun." >&2
  exit 1
fi
echo "Pushed main and $tag. release.yml will build and publish to PyPI."
