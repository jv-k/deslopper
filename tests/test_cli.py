import json
import os

from deslopper.cli import main


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
