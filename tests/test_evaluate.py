"""The eval harness: sandbox seeding, judges, exit codes.

The rewrite command under test is faked throughout (a copy, a no-op, a mangling
edit), so these tests stay deterministic. The real LLM invocation is exercised
only by an actual `deslopper eval` run.
"""

import os
import shutil
import sys

import pytest

from deslopper import evaluate, jev, ui
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


def test_raw_fixtures_trip_every_aggressive_tell(tmp_path):
    """The fixtures carry slop for the opt-in preset too, same contract."""
    cfg = resolve({"extends": ["deslopper:aggressive"]})
    expected = {t.name for t in cfg.tells}
    seed_sandbox(str(tmp_path))
    names = sorted(n for n in os.listdir(str(tmp_path)) if n.endswith(".md"))
    items = [(n, os.path.join(str(tmp_path), n)) for n in names]
    fired = {f.name for f in lint_files(items, cfg.tells).findings}
    assert expected <= fired, f"missing tells: {sorted(expected - fired)}"


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


# ── The plainness judge ───────────────────────────────────────────────────────
#
# Jev is faked at its transport, `jev.post`, with canned scores. Nothing below
# touches the network, and every test uses the plain palette so the lines can
# be matched byte for byte.

FAKE_KEY = "test-key-not-real"


def _touch_command(tmp_path):
    """A rewrite that records it ran and changes nothing."""
    marker = tmp_path / "ran"
    return f"touch {marker}", marker


def test_plainness_without_the_key_exits_two_before_the_rewrite(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv(jev.KEY_VAR, raising=False)
    command, marker = _touch_command(tmp_path)
    code = run_eval(command, plainness=True, pal=ui.PLAIN)
    err = capsys.readouterr().err
    assert code == 2
    assert jev.KEY_VAR in err
    assert not marker.exists()


def _scoring_transport(monkeypatch, scores, usage=(400, 0), cost="0.000066"):
    """Fake `jev.post`: answers every question with the next score in `scores`.

    One entry per pass, each a mapping of fixture name to score, or an
    exception to raise for that pass. Records every body it was handed.
    """
    monkeypatch.setenv(jev.KEY_VAR, FAKE_KEY)
    calls = []
    passes = list(scores)

    def post(body):
        calls.append(body)
        outcome = passes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        answers = {
            key: {"type": "score", "score": outcome[key], "probabilities": {}, "confidence": 0.9}
            for key in body["questions"]
        }
        return {
            "answers": answers,
            "usage": {"inputTokens": usage[0], "outputTokens": usage[1]},
            "providerMetadata": {"gateway": {"marketCost": cost}},
        }

    monkeypatch.setattr(jev, "post", post)
    return calls


BEFORE = {"overview.md": 0.12, "reference.md": 0.08, "template.md": 0.10}
AFTER = {"overview.md": 0.84, "reference.md": 0.80, "template.md": 0.79}


def test_plainness_scores_each_fixture_before_and_after(tmp_path, capsys, monkeypatch):
    calls = _scoring_transport(monkeypatch, [BEFORE, AFTER])
    code = run_eval(_fake_command(tmp_path, "clean"), plainness=True, pal=ui.PLAIN)
    out = capsys.readouterr().out
    assert code == 0
    lines = out.splitlines()
    assert lines[-4:] == [
        "ℹ plainness overview.md: 0.12 -> 0.84",
        "ℹ plainness reference.md: 0.08 -> 0.80",
        "ℹ plainness template.md: 0.10 -> 0.79",
        "ℹ plainness mean: 0.10 -> 0.81 | 800 tokens, $0.000132",
    ]
    # Two passes, one question per fixture keyed by name, three buckets each.
    assert len(calls) == 2
    for body in calls:
        assert sorted(body["questions"]) == ["overview.md", "reference.md", "template.md"]
        for name, question in body["questions"].items():
            assert question["type"] == "score"
            assert len(question["criteria"]) == 3
            assert name in body["state"]


def test_plainness_lines_come_after_the_findings_and_preservation_lines(tmp_path, capsys, monkeypatch):
    _scoring_transport(monkeypatch, [BEFORE, BEFORE])
    assert run_eval("true", plainness=True, pal=ui.PLAIN) == 1
    lines = capsys.readouterr().out.splitlines()
    last_finding = max(i for i, l in enumerate(lines) if "[warn]" in l or "[error]" in l)
    first_score = next(i for i, l in enumerate(lines) if "plainness " in l)
    assert last_finding < first_score

    _scoring_transport(monkeypatch, [BEFORE, AFTER])
    assert run_eval(_fake_command(tmp_path, "mangle"), plainness=True, pal=ui.PLAIN) == 3
    lines = capsys.readouterr().out.splitlines()
    preservation = lines.index("preservation: reference.md: fenced code differs")
    first_score = next(i for i, l in enumerate(lines) if "plainness " in l)
    assert preservation < first_score


LOW = {"overview.md": 0.01, "reference.md": 0.02, "template.md": 0.03}


@pytest.mark.parametrize(
    "mode, expected",
    [("clean", 0), (None, 1), ("mangle", 3)],
    ids=["pass", "efficacy-failure", "preservation-failure"],
)
def test_plainness_never_moves_the_exit_code(mode, expected, tmp_path, capsys, monkeypatch):
    """Low scores on every pass, and the code matches the run without the flag."""
    command = "true" if mode is None else _fake_command(tmp_path, mode)
    assert run_eval(command, pal=ui.PLAIN) == expected
    capsys.readouterr()
    _scoring_transport(monkeypatch, [LOW, LOW])
    assert run_eval(command, plainness=True, pal=ui.PLAIN) == expected
    assert "plainness mean: 0.02 -> 0.02" in capsys.readouterr().out


def test_plainness_prints_before_the_kept_sandbox_line(tmp_path, capsys, monkeypatch):
    _scoring_transport(monkeypatch, [BEFORE, AFTER])
    code = run_eval(_fake_command(tmp_path, "clean"), keep=True, plainness=True, pal=ui.PLAIN)
    captured = capsys.readouterr()
    assert code == 0
    kept = next(l for l in captured.err.splitlines() if "sandbox kept at " in l)
    shutil.rmtree(kept.split("sandbox kept at ", 1)[1].strip())
    # Scores go to stdout and the kept line to stderr, so the order is proven
    # by the streams' relative writes, captured here in one buffer each: the
    # mean line was fully written before the kept line existed.
    assert "plainness mean:" in captured.out
    assert captured.err.rstrip().endswith(kept.strip())


def test_plainness_survives_a_gateway_failure_on_the_after_pass(tmp_path, capsys, monkeypatch):
    _scoring_transport(monkeypatch, [BEFORE, jev.JevError("gateway returned 502")])
    code = run_eval(_fake_command(tmp_path, "clean"), plainness=True, pal=ui.PLAIN)
    captured = capsys.readouterr()
    assert code == 0
    assert "✖ plainness (after): gateway returned 502" in captured.err
    assert "ℹ plainness overview.md: 0.12" in captured.out
    assert "ℹ plainness mean: 0.10 | 400 tokens, $0.000066" in captured.out
    assert "-> " not in captured.out


def test_plainness_shows_only_the_after_score_when_the_baseline_failed(tmp_path, capsys, monkeypatch):
    _scoring_transport(monkeypatch, [jev.JevError("could not reach the gateway"), AFTER])
    code = run_eval(_fake_command(tmp_path, "clean"), plainness=True, pal=ui.PLAIN)
    captured = capsys.readouterr()
    assert code == 0
    assert "✖ plainness (baseline): could not reach the gateway" in captured.err
    assert "ℹ plainness overview.md: 0.84" in captured.out
    assert "ℹ plainness mean: 0.81 | 400 tokens, $0.000066" in captured.out


def _deleting_command(tmp_path, name):
    script = tmp_path / "delete_one.py"
    script.write_text(
        "import os, sys\nos.remove(os.path.join(sys.argv[2], sys.argv[1]))\n",
        encoding="utf-8",
    )
    return f"{sys.executable} {script} {name} {{dir}}"


def test_plainness_reports_a_deleted_fixture_as_unreadable(tmp_path, capsys, monkeypatch):
    calls = _scoring_transport(monkeypatch, [BEFORE, AFTER])
    code = run_eval(_deleting_command(tmp_path, "template.md"), plainness=True, pal=ui.PLAIN)
    captured = capsys.readouterr()
    assert code == 3
    assert "preservation: template.md: unreadable" in captured.out
    assert "ℹ plainness template.md: unreadable" in captured.out
    assert "ℹ plainness overview.md: 0.12 -> 0.84" in captured.out
    assert "ℹ plainness mean: 0.10 -> 0.82" in captured.out
    assert sorted(calls[1]["questions"]) == ["overview.md", "reference.md"]
