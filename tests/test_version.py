"""The version lives in three files and they have to agree.

A tool that bumps one and not the others leaves the tag pointing at the wrong version,
which release.yml only catches once the tag is public. That happened to v0.1.2. This runs
in CI and in the release gates, so it holds whichever tool does the bumping.
"""

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _pyproject_version():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version = "([^"]+)"', text, re.M).group(1)


def _module_version():
    text = (ROOT / "src" / "deslopper" / "__init__.py").read_text(encoding="utf-8")
    return re.search(r'^__version__ = "([^"]+)"', text, re.M).group(1)


def _package_json_version():
    return json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]


def test_the_three_version_files_agree():
    versions = {
        "pyproject.toml": _pyproject_version(),
        "src/deslopper/__init__.py": _module_version(),
        "package.json": _package_json_version(),
    }
    assert len(set(versions.values())) == 1, f"version drift: {versions}"
