#!/usr/bin/env python3
"""Bump the deslopper version across pyproject.toml, __init__.py, and package.json.

Usage: python3 scripts/bump.py [patch|minor|major]   (default: patch)

Edits the files in place and prints the new version. Review the diff, update CHANGELOG.md,
commit as `chore(release): vX.Y.Z`, then run `pnpm release` to tag and publish.
"""

import json
import pathlib
import re
import sys

LEVEL = sys.argv[1] if len(sys.argv) > 1 else "patch"
if LEVEL not in {"patch", "minor", "major"}:
    sys.exit(f"usage: bump.py [patch|minor|major]; got {LEVEL!r}")

root = pathlib.Path(__file__).resolve().parent.parent
pyproject = root / "pyproject.toml"
init = root / "src" / "deslopper" / "__init__.py"
pkg = root / "package.json"

text = pyproject.read_text(encoding="utf-8")
match = re.search(r'^version = "(\d+)\.(\d+)\.(\d+)"', text, re.M)
if not match:
    sys.exit("could not find a version in pyproject.toml")
major, minor, patch = (int(part) for part in match.groups())
if LEVEL == "major":
    major, minor, patch = major + 1, 0, 0
elif LEVEL == "minor":
    minor, patch = minor + 1, 0
else:
    patch += 1
new = f"{major}.{minor}.{patch}"

pyproject.write_text(
    re.sub(r'^version = "\d+\.\d+\.\d+"', f'version = "{new}"', text, count=1, flags=re.M),
    encoding="utf-8",
)
init.write_text(
    re.sub(
        r'__version__ = "\d+\.\d+\.\d+"',
        f'__version__ = "{new}"',
        init.read_text(encoding="utf-8"),
        count=1,
    ),
    encoding="utf-8",
)
data = json.loads(pkg.read_text(encoding="utf-8"))
data["version"] = new
pkg.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

print(new)
