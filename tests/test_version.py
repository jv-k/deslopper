"""The version lives in three files and they have to agree.

A tool that bumps one and not the others leaves the tag pointing at the wrong version,
which release.yml only catches once the tag is public. That happened to v0.1.2. This runs
in CI and in the release gates, so it holds whichever tool does the bumping.

Each version line also has to be the only one of its shape in the file. .ver-bumprc bumps
pyproject.toml and __init__.py by literal text pattern, so a second matching line would
leave ver-bump a choice of targets.
"""

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _sole_match(rel_path, pattern):
    text = (ROOT / rel_path).read_text(encoding="utf-8")
    found = re.findall(pattern, text, re.M)
    assert len(found) == 1, f"{rel_path}: expected one {pattern} line, found {len(found)}: {found}"
    return found[0]


def _pyproject_version():
    return _sole_match("pyproject.toml", r'^version = "([^"]+)"')


def _module_version():
    return _sole_match("src/deslopper/__init__.py", r'^__version__ = "([^"]+)"')


def _package_json_version():
    return json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]


def test_the_three_version_files_agree():
    versions = {
        "pyproject.toml": _pyproject_version(),
        "src/deslopper/__init__.py": _module_version(),
        "package.json": _package_json_version(),
    }
    assert len(set(versions.values())) == 1, f"version drift: {versions}"
