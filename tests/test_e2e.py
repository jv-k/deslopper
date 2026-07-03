"""End-to-end tests that drive the real CLI as a subprocess.

Unlike test_cli.py (which calls main() in-process), these spawn
`python -m deslopper`, exercising the packaged entrypoint, argv parsing,
real stdout/stderr, and the process exit status a shell would see.
"""

import json
import os
import shutil
import subprocess
import sys

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _run(args, cwd):
    return subprocess.run(
        [sys.executable, "-m", "deslopper", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def _stage(tmp_path, *names):
    """Copy fixtures into an isolated dir so the repo config can't interfere."""
    for name in names:
        shutil.copy(os.path.join(FIXTURES, name), tmp_path / name)
    return str(tmp_path)


def test_lint_slop_exits_one_and_reports(tmp_path):
    cwd = _stage(tmp_path, "ai_slop.md")
    proc = _run(["lint", "ai_slop.md"], cwd)
    assert proc.returncode == 1
    assert "em-dash" in proc.stdout
    assert "filler-verb" in proc.stdout
    assert "error(s)" in proc.stderr


def test_clean_file_exits_zero(tmp_path):
    (tmp_path / "clean.md").write_text("This sentence is plain and fine.\n", encoding="utf-8")
    proc = _run(["lint", "clean.md"], str(tmp_path))
    assert proc.returncode == 0


def test_json_output_is_parseable(tmp_path):
    cwd = _stage(tmp_path, "ai_slop.md")
    proc = _run(["lint", "--format", "json", "ai_slop.md"], cwd)
    payload = json.loads(proc.stdout)
    assert payload["summary"]["errors"] >= 1


def test_every_tell_fires_across_the_corpus(tmp_path):
    cwd = _stage(tmp_path, "ai_slop.md", "ai_slop_entities.md")
    proc = _run(["lint", "--format", "json", "ai_slop.md", "ai_slop_entities.md"], cwd)
    names = {f["name"] for f in json.loads(proc.stdout)["findings"]}
    expected = {
        "em-dash",
        "section-sign",
        "bold-bullet-lead",
        "semicolon",
        "not-just-x-but-y",
        "filler-verb",
        "marketing-adjective",
        "throat-clearing",
        "vague-intensifier",
        "emoji",
    }
    assert expected <= names, f"missing tells: {sorted(expected - names)}"


def test_module_entrypoint_runs():
    """`python -m deslopper` (the __main__ shim) is wired up."""
    proc = subprocess.run(
        [sys.executable, "-m", "deslopper", "rules"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "em-dash" in proc.stdout
