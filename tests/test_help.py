"""The help system, driven through main(argv) with captured stdio."""

import json

import pytest

from deslopper import __version__, gum
from deslopper.cli import main

ANSI = "\x1b["
WORDMARK_CHUNK = "┳━┓"  # the "d" of the wordmark


def run(args, capsys):
    code = main(args)
    out = capsys.readouterr()
    return code, out.out, out.err


def test_root_help_shows_banner_and_sections(capsys):
    code, out, _ = run(["--help"], capsys)
    assert code == 0
    assert WORDMARK_CHUNK in out
    assert f"deslopper v{__version__}" in out
    for section in ("USAGE", "COMMANDS", "EXAMPLES"):
        assert section in out
    for command in ("lint", "check", "rules", "init", "eval"):
        assert command in out


def test_root_help_piped_is_plain(capsys, monkeypatch):
    monkeypatch.delenv("CLICOLOR_FORCE", raising=False)
    _, out, _ = run(["-h"], capsys)
    assert ANSI not in out


# The wordmark's gradient, worked out here apart from ui.py: yellow, green and cyan,
# blended across the cells, each row starting 2 columns further along.
STOPS = ((255, 216, 102), (169, 220, 118), (120, 220, 232))


def _blend(t):
    at = t * (len(STOPS) - 1)
    i = min(int(at), len(STOPS) - 2)
    return "#%02x%02x%02x" % tuple(
        round(a + (b - a) * (at - i)) for a, b in zip(STOPS[i], STOPS[i + 1]))


def test_attended_root_help_draws_the_wordmark_in_a_diagonal_gradient(capsys, gum_shim):
    from deslopper.help import WORDMARK
    _, out, _ = run(["--help"], capsys)
    rows = ["".join(row) for row in WORDMARK]
    span = len(rows[0]) - 1 + 2 * (len(rows) - 1)
    for y, row in enumerate(rows):
        drawn = "".join('{{ Color "%s" %s }}' % (_blend((x + 2 * y) / span),
                                                 json.dumps(cell, ensure_ascii=False))
                        for x, cell in enumerate(row) if cell != " ")
        assert drawn in out.replace('{{ " " }}', ""), (y, out[:600])
    assert '{{ Color "#ffd866" "┳" }}' in out  # the first cell is yellow
    assert '{{ Color "#78dce8" "╸" }}' in out  # the last cell, the R's foot, is cyan
    assert ("┏━┓", "┣┳┛", "╹┗╸") == tuple(row[-1] for row in WORDMARK)  # the R


def test_attended_root_help_is_drawn_by_gum_with_pills(capsys, gum_shim):
    _, out, _ = run(["--help"], capsys)
    assert [c["args"][0] for c in gum_shim()] == ["format"]
    assert '{{ Bold (Color "%s" "%s" " USAGE ") }}' % (
        gum.PALETTE["on-accent"], gum.PALETTE["accent"]) in out  # section pill
    assert f'" deslopper v{__version__} "' in out  # version pill


def test_no_color_keeps_help_plain_even_with_gum(capsys, gum_shim, monkeypatch):
    monkeypatch.delenv("CLICOLOR_FORCE")
    monkeypatch.setenv("NO_COLOR", "1")
    _, out, _ = run(["--help"], capsys)
    assert gum_shim() == []
    assert ANSI not in out and "{{" not in out


def test_attended_version_is_the_green_pill(capsys, gum_shim):
    code, out, _ = run(["--version"], capsys)
    assert code == 0
    assert '{{ Bold (Color "%s" "%s" " deslopper v%s ") }}' % (
        gum.PALETTE["on-accent"], gum.PALETTE["ok"], __version__) in out


def test_version_flag_piped_is_plain(capsys, monkeypatch):
    monkeypatch.delenv("CLICOLOR_FORCE", raising=False)
    code, out, _ = run(["--version"], capsys)
    assert code == 0
    assert ANSI not in out
    assert f"deslopper v{__version__}" in out


def test_bare_invocation_shows_help_and_exits_two(capsys):
    code, out, err = run([], capsys)
    assert code == 2
    assert out == ""
    assert "USAGE" in err
    assert WORDMARK_CHUNK in err


def test_bare_double_dash_behaves_like_bare(capsys):
    code, _, err = run(["--"], capsys)
    assert code == 2
    assert "USAGE" in err


@pytest.mark.parametrize("command", ["lint", "check", "rules", "init", "eval"])
def test_command_help_shows_options(command, capsys):
    code, out, _ = run([command, "--help"], capsys)
    assert code == 0
    assert "USAGE" in out
    assert "OPTIONS" in out
    assert f"deslopper {command}" in out


def test_command_help_after_other_args(capsys):
    code, out, _ = run(["lint", "somefile.md", "-h"], capsys)
    assert code == 0
    assert "OPTIONS" in out


def test_help_flag_after_double_dash_is_not_help(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, out, err = run(["lint", "--", "--help"], capsys)
    assert "USAGE" not in out
    assert "↳ cannot read --help" in err


def _visible_lines(text):
    return [line for line in text.splitlines()]


def test_piped_help_wraps_at_default_width(capsys, monkeypatch):
    monkeypatch.delenv("COLUMNS", raising=False)
    _, out, _ = run(["--help"], capsys)
    assert all(len(line) <= 80 for line in _visible_lines(out)), \
        max(_visible_lines(out), key=len)


def test_help_adapts_to_columns(capsys, monkeypatch):
    monkeypatch.setenv("COLUMNS", "60")
    _, out, _ = run(["--help"], capsys)
    assert all(len(line) <= 60 for line in _visible_lines(out)), \
        max(_visible_lines(out), key=len)


def test_command_help_adapts_to_columns(capsys, monkeypatch):
    monkeypatch.setenv("COLUMNS", "60")
    _, out, _ = run(["lint", "--help"], capsys)
    assert all(len(line) <= 60 for line in _visible_lines(out)), \
        max(_visible_lines(out), key=len)


def test_wide_columns_keep_rows_on_one_line(capsys, monkeypatch):
    monkeypatch.setenv("COLUMNS", "200")
    _, out, _ = run(["--help"], capsys)
    assert "  Lint files and fail on smells." in out


def test_lint_help_lists_jev_and_check_help_does_not(capsys):
    _, lint_out, _ = run(["lint", "--help"], capsys)
    assert "--jev" in lint_out
    assert "AI_GATEWAY_API_KEY" in lint_out
    # --triage is a hidden alias for configs written before the rename.
    assert "--triage" not in lint_out
    _, check_out, _ = run(["check", "--help"], capsys)
    assert "--jev" not in check_out


def test_top_level_help_shows_a_jev_example(capsys):
    _, out, _ = run(["--help"], capsys)
    assert "deslopper lint --jev" in out


def test_eval_help_lists_the_plainness_flag(capsys):
    code, out, _ = run(["eval", "--help"], capsys)
    assert code == 0
    assert "--plainness" in out
    assert "--keep" in out
