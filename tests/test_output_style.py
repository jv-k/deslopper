"""The styled run output: the colour gate and the summary log line.

Everything drives the CLI seam — main(argv) with captured stdio — and the colour
gate only ever moves through the environment (NO_COLOR, FORCE_COLOR).
"""

import os

from deslopper.cli import main

ANSI = "\x1b["


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
    p.write_text(text, encoding="utf-8")
    return p


def test_piped_findings_are_plain(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("CLICOLOR_FORCE", raising=False)
    write(tmp_path, "a.md", "a — dash\n")
    _, out, err = run(["lint", "a.md"], str(tmp_path), capsys)
    assert "a.md:1:3 [error] em-dash:" in out
    assert ANSI not in out
    assert ANSI not in err


def test_force_color_styles_findings(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    write(tmp_path, "a.md", "a — dash\n")
    _, out, err = run(["lint", "a.md"], str(tmp_path), capsys)
    assert ANSI in out
    assert "[error]" in out
    assert ANSI in err


def test_no_color_beats_force_color(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("NO_COLOR", "1")
    write(tmp_path, "a.md", "a — dash\n")
    _, out, err = run(["lint", "a.md"], str(tmp_path), capsys)
    assert ANSI not in out
    assert ANSI not in err


def test_machine_formats_never_styled(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    write(tmp_path, "a.md", "a — dash\n")
    _, out, _ = run(["lint", "--format", "json", "a.md"], str(tmp_path), capsys)
    assert ANSI not in out
    _, out, _ = run(["lint", "--format", "github", "a.md"], str(tmp_path), capsys)
    assert ANSI not in out


def test_clean_lint_summary_is_a_success_line(tmp_path, capsys):
    write(tmp_path, "a.md", "all good here\n")
    code, _, err = run(["lint", "a.md"], str(tmp_path), capsys)
    assert code == 0
    assert "✔ no slop found" in err


def test_error_summary_is_an_error_line(tmp_path, capsys):
    write(tmp_path, "a.md", "a — dash\n")
    code, _, err = run(["lint", "a.md"], str(tmp_path), capsys)
    assert code == 1
    assert "✖ 1 error(s), 0 warning(s)" in err


def test_warn_only_summary_is_a_warn_line(tmp_path, capsys):
    write(tmp_path, "a.md", "a; b\n")
    code, _, err = run(["lint", "a.md"], str(tmp_path), capsys)
    assert code == 0
    assert "! 0 error(s), 1 warning(s)" in err


def test_strict_tag_survives(tmp_path, capsys):
    write(tmp_path, "a.md", "a; b\n")
    _, _, err = run(["lint", "--strict", "a.md"], str(tmp_path), capsys)
    assert "[strict]" in err


def test_unreadable_path_is_a_trace_line(tmp_path, capsys):
    write(tmp_path, "a.md", "ok\n")
    code, _, err = run(["lint", "a.md", "missing.md"], str(tmp_path), capsys)
    assert code == 1
    assert "↳ cannot read missing.md" in err
    assert "1 unreadable" in err


def test_rules_piped_keeps_tsv(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    code, out, _ = run(["rules"], str(tmp_path), capsys)
    assert code == 0
    assert "em-dash\terror\t" in out
    assert ANSI not in out


def test_rules_forced_color_aligns_and_styles(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    code, out, _ = run(["rules"], str(tmp_path), capsys)
    assert code == 0
    assert ANSI in out
    assert "\t" not in out


def test_init_confirms_with_a_success_line(tmp_path, capsys):
    code, out, _ = run(["init"], str(tmp_path), capsys)
    assert code == 0
    assert "✔ wrote deslopper.config.json" in out


def test_usage_error_is_an_error_line(tmp_path, capsys):
    run(["init"], str(tmp_path), capsys)
    code, _, err = run(["init"], str(tmp_path), capsys)
    assert code == 2
    assert "✖ deslopper.config.json already exists" in err


def test_eval_verdict_speaks_through_log_lines(tmp_path, capsys):
    code, _, err = run(["eval", "true"], str(tmp_path), capsys)
    assert code == 1
    assert "✖ eval FAIL (efficacy)" in err
    assert "ℹ seeded" in err


def test_rules_with_no_tells_prints_nothing(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    write(tmp_path, "deslopper.config.json", '{"extends": []}')
    code, out, _ = run(["rules"], str(tmp_path), capsys)
    assert code == 0
    assert out == ""


def test_styled_rules_wrap_to_the_width(tmp_path, capsys, monkeypatch):
    import re
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "100")
    code, out, _ = run(["rules"], str(tmp_path), capsys)
    assert code == 0
    visible = [re.sub(r"\x1b\[[0-9;]*m", "", line) for line in out.splitlines()]
    too_wide = [line for line in visible if len(line) > 100]
    assert not too_wide, too_wide[0]
