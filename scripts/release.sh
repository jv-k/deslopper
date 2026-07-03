#!/usr/bin/env bash
# Tag and push a deslopper release. Bump the version and commit it first (see scripts/bump.py).
# Runs the same gates as .github/workflows/release.yml (tests, lint, version check) so a
# failure surfaces before the tag exists, then pushes the branch and the tag. The pushed tag
# triggers release.yml, which builds and publishes to PyPI.
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

if [ -x .venv/bin/python ]; then
  py=.venv/bin/python
else
  py=python3
fi

"$py" -m pytest -q
"$py" -m deslopper lint

module_version="$("$py" -c 'import deslopper; print(deslopper.__version__)')"
if [ "$module_version" != "$version" ]; then
  echo "pyproject.toml has $version but deslopper.__version__ is $module_version; run scripts/bump.py" >&2
  exit 1
fi

tag="v$version"
if git rev-parse "$tag" >/dev/null 2>&1; then
  echo "tag $tag already exists" >&2
  exit 1
fi

echo "Releasing $tag"
git push origin HEAD
git tag "$tag"
git push origin "$tag"
echo "Pushed the branch and $tag. release.yml will build and publish to PyPI."
