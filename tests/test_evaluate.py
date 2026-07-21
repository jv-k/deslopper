"""The eval harness: sandbox seeding, judges, exit codes.

The rewrite command under test is faked throughout (a copy, a no-op, a mangling
edit), so these tests stay deterministic. The real LLM invocation is exercised
only by an actual `deslopper eval` run.
"""

import os
import shutil
import sys

from deslopper import evaluate
from deslopper.config import resolve
from deslopper.engine import lint_files
from deslopper.evaluate import run_eval, seed_sandbox

def _lint_dir(path):
    cfg = resolve({})
    names = sorted(n for n in os.listdir(path) if n.endswith(".md"))
    items = [(n, os.path.join(path, n)) for n in names]
    return lint_files(items, cfg.tells)


def test_seed_sandbox_plants_the_fixtures_as_markdown(tmp_path):
    seeded = seed_sandbox(str(tmp_path))
    assert seeded == ["overview.md", "reference.md", "template.md"]
    for name in seeded:
        assert (tmp_path / name).is_file()


def test_raw_fixtures_trip_every_tell(tmp_path):
    """The red baseline: the seeded fixtures must fire every recommended tell.

    Derived from the preset on purpose: adding a tell without seeding the eval
    fixtures with its slop fails here.
    """
    expected = {t.name for t in resolve({}).tells}
    seed_sandbox(str(tmp_path))
    result = _lint_dir(str(tmp_path))
    names = {f.name for f in result.findings}
    assert expected <= names, f"missing tells: {sorted(expected - names)}"
    assert result.errors >= 1


# A stand-in for the LLM rewrite pass. `clean` keeps every protected line (front
# matter, fences, headings, table rows, lines holding a link) and replaces the
# rest with plain prose; `mangle` cleans and then edits inside a fence.
FAKE_REWRITE = """\
import os, sys

mode, target = sys.argv[1], sys.argv[2]
for name in sorted(os.listdir(target)):
    if not name.endswith(".md"):
        continue
    path = os.path.join(target, name)
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    out, in_fence, in_front = [], False, False
    for idx, line in enumerate(lines):
        if idx == 0 and line.strip() == "---":
            in_front = True
            out.append(line)
            continue
        if in_front:
            out.append(line)
            if line.strip() in ("---", "..."):
                in_front = False
            continue
        if line.lstrip().startswith("```"):
            out.append(line)
            in_fence = not in_fence
            continue
        keep = (
            in_fence
            or line.startswith("#")
            or line.lstrip().startswith("|")
            or "](" in line
            or not line.strip()
        )
        out.append(line if keep else "Plain text.")
    text = "\\n".join(out) + "\\n"
    if mode == "mangle" and name == "reference.md":
        text = text.replace("retry \\u2014 twice", "retry - twice")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
"""


def _fake_command(tmp_path, mode):
    script = tmp_path / "fake_rewrite.py"
    script.write_text(FAKE_REWRITE, encoding="utf-8")
    return f"{sys.executable} {script} {mode} {{dir}}"


def test_eval_passes_with_a_perfect_rewrite(tmp_path, capsys):
    assert run_eval(_fake_command(tmp_path, "clean")) == 0


def test_eval_fails_efficacy_when_nothing_changes(capsys):
    code = run_eval("true")
    out = capsys.readouterr().out
    assert code == 1
    assert "overview.md:" in out
    assert "em-dash" in out


def test_eval_fails_preservation_when_a_fence_changes(tmp_path, capsys):
    code = run_eval(_fake_command(tmp_path, "mangle"))
    out = capsys.readouterr().out
    assert code == 3
    assert "reference.md: fenced code differs" in out


def test_a_failing_command_still_judges_but_exits_broken(capsys):
    """4 wins over the judges, but the sandbox is still judged and reported."""
    code = run_eval("false")
    captured = capsys.readouterr()
    assert code == 4
    assert "harness broken" in captured.err
    assert "overview.md:" in captured.out


def _seed_one_file(text):
    def seed(dest):
        with open(os.path.join(dest, "only.md"), "w", encoding="utf-8") as fh:
            fh.write(text)
        return ["only.md"]

    return seed


def test_eval_reports_broken_harness_on_an_errorless_baseline(monkeypatch, capsys):
    monkeypatch.setattr(evaluate, "seed_sandbox", _seed_one_file("Nothing to find here.\n"))
    code = run_eval("true")
    err = capsys.readouterr().err
    assert code == 4
    assert "harness broken" in err


def test_eval_reports_broken_harness_on_a_warnless_baseline(monkeypatch, capsys):
    """With no warn-tier slop the strictly-below gate can never pass."""
    monkeypatch.setattr(evaluate, "seed_sandbox", _seed_one_file("An em dash — here.\n"))
    code = run_eval("true")
    err = capsys.readouterr().err
    assert code == 4
    assert "harness broken" in err


def test_keep_leaves_the_sandbox_on_disk(capsys):
    code = run_eval("true", keep=True)
    err = capsys.readouterr().err
    assert code == 1
    marker = "sandbox kept at "
    line = next(l for l in err.splitlines() if marker in l)
    path = line.split(marker, 1)[1].strip()
    assert os.path.isdir(path)
    shutil.rmtree(path)
