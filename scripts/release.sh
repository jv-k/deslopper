#!/usr/bin/env bash
# Tag and push a deslopper release. Bump the version and commit it first (see scripts/bump.py).
# The pushed tag triggers .github/workflows/release.yml, which builds and publishes to PyPI.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -n "$(git status --porcelain)" ]; then
  echo "working tree is not clean; commit the version bump first" >&2
  exit 1
fi

version="$(grep -m1 '^version = ' pyproject.toml | sed -E 's/version = "([^"]+)"/\1/')"
if [ -z "$version" ]; then
  echo "could not read the version from pyproject.toml" >&2
  exit 1
fi

if [ -x .venv/bin/pytest ]; then
  .venv/bin/pytest -q
else
  python3 -m pytest -q
fi

tag="v$version"
if git rev-parse "$tag" >/dev/null 2>&1; then
  echo "tag $tag already exists" >&2
  exit 1
fi

echo "Releasing $tag"
git tag "$tag"
git push origin "$tag"
echo "Pushed $tag. release.yml will build and publish to PyPI."
