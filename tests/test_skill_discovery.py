"""Red cases for scripts/check-skill-discovery.sh, run against a stub `npx` on PATH.

The real check calls the skills CLI over the network. These cases replace `npx` with a
script that prints canned listing output, so they run offline and pin the assertions:
exactly one skill, and that skill named deslopper as a whole line.
"""
import os
import shutil
import stat
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "check-skill-discovery.sh")

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")

ESC = "\x1b"
# The skills CLI redraws its spinner in place. Captured from 1.7.x on a pipe, it moves the
# cursor to column 1 and erases (ESC[1G ESC[J). On a terminal it can use a carriage return.
REDRAW_ESC = f"{ESC}[1G{ESC}[J"
REDRAW_CR = "\r"

HEAD = (
    "\n│\n"
    f"{ESC}[?25l│\n◇  Source: /home/runner/work/deslopper/deslopper\n"
    f"{ESC}[?25h{ESC}[?25l│\n◇  Local path validated\n"
    f"{ESC}[?25h{ESC}[?25l│\n"
)
TAIL = (
    f"\n{ESC}[?25h\n│\n◇  Available Skills\n│\n│    deslopper\n│\n"
    "│      Write prose free of the mechanical tells of machine-generated text.\n│\n"
)


def _listing(found, redraw=None, frames=3, tail=TAIL):
    spinner = ""
    if redraw is not None:
        spinner = "".join(f"◒  Discovering skills…{redraw}" for _ in range(frames))
    return HEAD + spinner + f"◇  {found}" + tail


def _run(tmp_path, output):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    canned = tmp_path / "listing.out"
    canned.write_bytes(output.encode("utf-8"))
    npx = bindir / "npx"
    npx.write_text(f'#!/usr/bin/env bash\ncat "{canned}"\n')
    npx.chmod(npx.stat().st_mode | stat.S_IXUSR)
    env = dict(os.environ, PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}")
    return subprocess.run(["bash", SCRIPT, ROOT], env=env, capture_output=True, text=True)


def test_passes_on_a_plain_listing(tmp_path):
    proc = _run(tmp_path, _listing("Found 1 skill"))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "skill discovery ok" in proc.stdout


@pytest.mark.parametrize("redraw", [REDRAW_ESC, REDRAW_CR], ids=["esc-1g", "carriage-return"])
def test_passes_with_spinner_frames_on_the_result_line(tmp_path, redraw):
    proc = _run(tmp_path, _listing("Found 1 skill", redraw=redraw))
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.parametrize("redraw", [None, REDRAW_ESC, REDRAW_CR], ids=["plain", "esc-1g", "carriage-return"])
def test_fails_when_more_than_one_skill_is_found(tmp_path, redraw):
    proc = _run(tmp_path, _listing("Found 2 skills", redraw=redraw))
    assert proc.returncode == 1
    assert "expected exactly one discovered skill" in proc.stderr


@pytest.mark.parametrize("redraw", [None, REDRAW_ESC, REDRAW_CR], ids=["plain", "esc-1g", "carriage-return"])
def test_fails_when_the_count_is_only_a_prefix(tmp_path, redraw):
    proc = _run(tmp_path, _listing("Found 10 skills", redraw=redraw))
    assert proc.returncode == 1
    assert "expected exactly one discovered skill" in proc.stderr


def test_fails_when_deslopper_appears_only_inside_another_line(tmp_path):
    # The source path holds "deslopper" on CI, so a name match anywhere would pass falsely.
    tail = f"\n{ESC}[?25h\n│\n◇  Available Skills\n│\n│    other-skill\n│\n"
    proc = _run(tmp_path, _listing("Found 1 skill", redraw=REDRAW_ESC, tail=tail))
    assert proc.returncode == 1
    assert "expected the discovered skill to be deslopper" in proc.stderr
