"""The run output: the plain lines, and the gum layer an attended run adds over them.

Everything drives the CLI seam, main(argv) with captured stdio. Whether a run is
attended moves only through the environment (NO_COLOR, CLICOLOR_FORCE) and conftest's
gum shim.
"""

import os

from deslopper import gum
from deslopper.cli import main
from tests.conftest import canned_jev

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
    monkeypatch.delenv("CLICOLOR_FORCE", raising=False)
    write(tmp_path, "a.md", "a — dash\n")
    _, out, err = run(["lint", "a.md"], str(tmp_path), capsys)
    assert "a.md:1:3 [error] em-dash:" in out
    assert ANSI not in out
    assert ANSI not in err


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
    code, out, _ = run(["rules"], str(tmp_path), capsys)
    assert code == 0
    assert "em-dash\terror\t" in out
    assert ANSI not in out


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
    write(tmp_path, "deslopper.config.json", '{"extends": []}')
    code, out, _ = run(["rules"], str(tmp_path), capsys)
    assert code == 0
    assert out == ""


def test_piped_triage_keeps_the_number_and_no_glyphs(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("CLICOLOR_FORCE", raising=False)
    canned_jev(monkeypatch, [("keep", 0.93)])
    write(tmp_path, "a.md", "a — dash\n")
    _, out, _ = run(["lint", "--jev", "a.md"], str(tmp_path), capsys)
    assert out.rstrip().endswith("[keep 0.93]")
    assert ANSI not in out


# The gum layer. gum_shim forces an attended run and records each gum call.


def _calls_of(calls, sub):
    return [c for c in calls() if c["args"][0] == sub]


def _record_spins(monkeypatch):
    """The spinner titles the CLI asks for. gum.spin itself is tested in test_gum."""
    from contextlib import nullcontext
    from deslopper import gum
    titles = []
    monkeypatch.setattr(gum, "spin", lambda title, stream=None: titles.append(title) or nullcontext())
    return titles


def test_attended_lint_draws_the_view_in_one_format_call_and_its_table(tmp_path, capsys, gum_shim):
    write(tmp_path, "a.md", "a — dash\nc; d\n")
    write(tmp_path, "b.md", "e; f\n")
    code, out, err = run(["lint", "a.md", "b.md"], str(tmp_path), capsys)
    assert code == 1
    assert [c["args"][0] for c in gum_shim()] == ["format", "table"]
    # The header, a section per file, the totals and the summary table, in one view.
    assert '" deslopper "' in out and '"2 files, 2 with slop"' in out
    assert '"a.md"' in out and '"b.md"' in out
    assert '"1 error"' in out and '"2 warnings"' in out
    # The plain lines and the stderr summary give way to the view.
    assert "a.md:1:3 [error]" not in out
    assert err == ""


def test_attended_view_shows_the_line_and_a_caret(tmp_path, capsys, gum_shim):
    write(tmp_path, "a.md", "a — dash\n")
    _, out, _ = run(["lint", "a.md"], str(tmp_path), capsys)
    assert '"a "' in out and '"—"' in out and '" dash"' in out
    assert '"^"' in out


def test_attended_check_draws_the_view_and_exits_zero(tmp_path, capsys, gum_shim):
    write(tmp_path, "a.md", "a — dash\n")
    code, out, _ = run(["check", "a.md"], str(tmp_path), capsys)
    assert code == 0
    assert '{{ Bold "check" }}' in out


def test_attended_jev_spins_per_file_and_rates_each_place(tmp_path, capsys, gum_shim, monkeypatch):
    canned_jev(monkeypatch, [("keep", 0.93), ("rewrite", 0.62), ("keep", 0.8)])
    spins = _record_spins(monkeypatch)
    write(tmp_path, "a.md", "a — dash\nc; d\n")
    write(tmp_path, "b.md", "e; f\n")
    _, out, err = run(["lint", "--jev", "a.md", "b.md"], str(tmp_path), capsys)
    assert spins == ["(1/2) Asking Jev about 2 findings in a.md",
                     "(2/2) Asking Jev about 1 finding in b.md"]
    assert '{{ " 0.93 " }}{{ Faint "keep" }}' in out
    assert '"keep" }}\t{{ "2" }}' in out
    assert '"this run" }}\t{{ "3" }}\t{{ "3,154" }}\t{{ "$0.00013" }}' in out
    assert err == ""


def test_attended_rules_draw_one_gum_view(tmp_path, capsys, gum_shim):
    code, out, _ = run(["rules"], str(tmp_path), capsys)
    assert code == 0
    assert len(_calls_of(gum_shim, "format")) == 1
    assert '{{ Bold "em-dash' in out
    assert "\t" not in out


def test_attended_lint_falls_back_to_plain_output_when_gum_fails(tmp_path, capsys, gum_shim, monkeypatch):
    monkeypatch.setenv("GUM_SHIM_FAIL", "1")
    write(tmp_path, "a.md", "a — dash\n")
    code, out, err = run(["lint", "a.md"], str(tmp_path), capsys)
    assert code == 1
    assert out == "a.md:1:3 [error] em-dash: em dash in prose, use a colon, comma, parentheses, or two sentences\n"
    assert "✖ 1 error(s), 0 warning(s)" in err
    assert "something broke" not in out + err


def test_attended_check_and_rules_fall_back_when_gum_fails(tmp_path, capsys, gum_shim, monkeypatch):
    monkeypatch.setenv("GUM_SHIM_FAIL", "1")
    write(tmp_path, "a.md", "a — dash\n")
    code, out, _ = run(["check", "a.md"], str(tmp_path), capsys)
    assert code == 0 and out.startswith("a.md:1:3 [error] em-dash:")
    code, out, _ = run(["rules"], str(tmp_path), capsys)
    assert code == 0 and "em-dash\terror\t" in out


def test_attended_eval_draws_the_remaining_findings_as_the_lint_view(tmp_path, capsys, gum_shim):
    code, out, err = run(["eval", "true"], str(tmp_path), capsys)
    assert code == 1
    assert '{{ Bold "eval" }}' in out and '" deslopper "' in out
    assert "[error]" not in out  # the plain lines give way to the view
    assert "eval FAIL (efficacy)" in err


def test_attended_status_lines_colour_their_icon(tmp_path, capsys, gum_shim):
    code, out, _ = run(["init"], str(tmp_path), capsys)
    assert code == 0
    assert '{{ Color "%s" "✔" }}{{ " wrote deslopper.config.json" }}' % gum.PALETTE["ok"] in out


def test_machine_formats_never_call_gum(tmp_path, capsys, gum_shim):
    write(tmp_path, "a.md", "a — dash\n")
    run(["lint", "--format", "json", "a.md"], str(tmp_path), capsys)
    run(["lint", "--format", "github", "a.md"], str(tmp_path), capsys)
    run(["rules", "--format", "json"], str(tmp_path), capsys)
    assert gum_shim() == []


def test_a_forced_run_without_gum_prints_plain_and_one_hint(tmp_path, capsys, monkeypatch):
    from deslopper import gum
    monkeypatch.setenv("CLICOLOR_FORCE", "1")
    write(tmp_path, "a.md", "a — dash\n")
    _, out, err = run(["lint", "a.md"], str(tmp_path), capsys)
    assert "a.md:1:3 [error] em-dash:" in out
    assert err.count(gum.HINT) == 1
