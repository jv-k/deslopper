import json
import os

import pytest

from deslopper.cli import main
from tests.conftest import canned_jev, check_finding, finding_schema


def run(args, cwd, capsys):
    old = os.getcwd()
    os.chdir(cwd)
    try:
        code = main(args)
    finally:
        os.chdir(old)
    out = capsys.readouterr()
    return code, out.out, out.err


def write(tmp_path, rel, text):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_lint_reports_and_exits_one_on_error(tmp_path, capsys):
    write(tmp_path, "a.md", "a — dash\n")
    code, out, err = run(["lint", "a.md"], str(tmp_path), capsys)
    assert code == 1
    assert "a.md:1:3 [error] em-dash:" in out
    assert "1 error(s)" in err


def test_check_exits_zero_on_findings(tmp_path, capsys):
    write(tmp_path, "a.md", "a — dash\n")
    code, _, _ = run(["check", "a.md"], str(tmp_path), capsys)
    assert code == 0


def test_lint_clean_exits_zero(tmp_path, capsys):
    write(tmp_path, "a.md", "all good here\n")
    code, _, _ = run(["lint", "a.md"], str(tmp_path), capsys)
    assert code == 0


def test_strict_fails_on_warn(tmp_path, capsys):
    write(tmp_path, "a.md", "a; b\n")
    assert run(["lint", "a.md"], str(tmp_path), capsys)[0] == 0
    assert run(["lint", "--strict", "a.md"], str(tmp_path), capsys)[0] == 1


def test_format_json(tmp_path, capsys):
    write(tmp_path, "a.md", "a — b\n")
    code, out, _ = run(["lint", "--format", "json", "a.md"], str(tmp_path), capsys)
    payload = json.loads(out)
    assert payload["summary"]["errors"] == 1


def test_config_error_exits_two(tmp_path, capsys):
    write(tmp_path, "deslopper.config.json", '{"plugins": ["x"]}')
    write(tmp_path, "a.md", "ok\n")
    code, _, err = run(["lint", "a.md"], str(tmp_path), capsys)
    assert code == 2
    assert "plugins" in err


def test_rules_lists_tells(tmp_path, capsys):
    code, out, _ = run(["rules"], str(tmp_path), capsys)
    assert code == 0
    assert "em-dash" in out
    assert "bold-bullet-lead" in out


def test_eval_runs_the_harness_against_the_command(tmp_path, capsys):
    code, out, err = run(["eval", "true"], str(tmp_path), capsys)
    assert code == 1
    assert "em-dash" in out
    assert "FAIL (efficacy)" in err


def test_init_writes_then_refuses(tmp_path, capsys):
    code, _, _ = run(["init"], str(tmp_path), capsys)
    assert code == 0
    assert (tmp_path / "deslopper.config.json").exists()
    code2, _, err2 = run(["init"], str(tmp_path), capsys)
    assert code2 == 2
    assert "exists" in err2


# --triage: the scan runs as today, then Jev annotates each finding.


def test_triage_appends_the_verdict_to_each_text_line_and_the_summary(tmp_path, capsys, monkeypatch):
    calls = canned_jev(monkeypatch, [("keep", 0.93), ("rewrite", 0.88)])
    write(tmp_path, "a.md", "a — b\nc; d\n")
    code, out, err = run(["lint", "--triage", "a.md"], str(tmp_path), capsys)
    assert code == 1
    assert out.splitlines() == [
        "a.md:1:3 [error] em-dash: em dash in prose, use a colon, comma, parentheses,"
        " or two sentences [keep 0.93]",
        "a.md:2:2 [warn] semicolon: semicolon in prose, prefer a full stop [rewrite 0.88]",
    ]
    assert "1 error(s), 1 warning(s) · triage: 1 keep, 1 rewrite · 1577 tokens, $0.000066" in err
    assert len(calls) == 1


def test_triage_json_carries_the_verdict_fields_and_validates(tmp_path, capsys, monkeypatch):
    canned_jev(monkeypatch, [("keep", 0.93), ("rewrite", 0.88)])
    write(tmp_path, "a.md", "a — b\nc; d\n")
    code, out, _ = run(["lint", "--triage", "--format", "json", "a.md"], str(tmp_path), capsys)
    payload = json.loads(out)
    assert [(f["verdict"], f["probability"]) for f in payload["findings"]] == [
        ("keep", 0.93), ("rewrite", 0.88),
    ]
    schema = finding_schema()
    for item in payload["findings"]:
        check_finding(item, schema)
    assert code == 1


def test_triage_github_folds_the_verdict_into_the_annotation(tmp_path, capsys, monkeypatch):
    canned_jev(monkeypatch, [("rewrite", 0.88)])
    write(tmp_path, "a.md", "c; d\n")
    _, out, _ = run(["lint", "--triage", "--format", "github", "a.md"], str(tmp_path), capsys)
    assert out == ("::warning file=a.md,line=1,col=2::semicolon - "
                   "semicolon in prose, prefer a full stop [rewrite 0.88]\n")


@pytest.mark.parametrize("text, extra", [
    ("a — b\n", []),          # an error: 1 either way
    ("c; d\n", []),           # warnings only: 0 either way
    ("c; d\n", ["--strict"]), # warnings under strict: 1 either way
])
def test_triage_never_moves_the_exit_code(tmp_path, capsys, monkeypatch, text, extra):
    # Every verdict is keep, the answer most likely to tempt a demotion.
    canned_jev(monkeypatch, [("keep", 0.99)])
    write(tmp_path, "a.md", text)
    plain = run(["lint", *extra, "a.md"], str(tmp_path), capsys)[0]
    judged = run(["lint", "--triage", *extra, "a.md"], str(tmp_path), capsys)[0]
    assert judged == plain


def test_triage_without_the_key_prints_one_hint_and_no_findings(tmp_path, capsys, monkeypatch):
    from deslopper import jev

    monkeypatch.delenv("AI_GATEWAY_API_KEY", raising=False)
    calls = []
    monkeypatch.setattr(jev, "post", lambda body: calls.append(body))
    write(tmp_path, "a.md", "a — b\n")
    code, out, err = run(["lint", "--triage", "a.md"], str(tmp_path), capsys)
    assert code == 2
    assert out == ""
    assert len(err.splitlines()) == 1
    assert "AI_GATEWAY_API_KEY" in err
    assert calls == []


def test_triage_gateway_failure_prints_one_line_and_keeps_the_scan_exit_code(tmp_path, capsys, monkeypatch):
    from deslopper import jev

    monkeypatch.setenv("AI_GATEWAY_API_KEY", "test-key-not-real")
    calls = []

    def post(body):
        calls.append(body)
        if len(calls) == 2:
            raise jev.JevError("gateway returned 500: boom")
        return {"answers": {k: {"type": "choice", "choice": "keep",
                                "probabilities": {"keep": 0.9, "rewrite": 0.1}}
                            for k in body["questions"]}}

    monkeypatch.setattr(jev, "post", post)
    write(tmp_path, "a.md", "c; d\n")
    write(tmp_path, "b.md", "e; f\n")
    code, out, err = run(["lint", "--triage", "a.md", "b.md"], str(tmp_path), capsys)
    assert code == 0
    lines = out.splitlines()
    assert lines[0].endswith("[keep 0.90]")
    assert "[" not in lines[1].split("semicolon: ")[1]
    assert sum("boom" in line for line in err.splitlines()) == 1
    assert "triage: 1 keep, 0 rewrite" in err


def test_triage_clean_files_make_no_request(tmp_path, capsys, monkeypatch):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    write(tmp_path, "a.md", "all good here\n")
    code, _, err = run(["lint", "--triage", "a.md"], str(tmp_path), capsys)
    assert code == 0
    assert calls == []
    assert "no slop found" in err


def test_check_does_not_accept_triage(tmp_path, capsys):
    write(tmp_path, "a.md", "a — b\n")
    with pytest.raises(SystemExit):
        run(["check", "--triage", "a.md"], str(tmp_path), capsys)
