"""The help system, driven through main(argv) with captured stdio."""

import pytest

from deslopper import __version__
from deslopper.cli import main

ANSI = "\x1b["
WORDMARK_CHUNK = "╺┳┓"  # the "d" of the figlet-future wordmark


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
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("CLICOLOR_FORCE", raising=False)
    _, out, _ = run(["-h"], capsys)
    assert ANSI not in out


def test_root_help_forced_color_has_pills_and_rainbow(capsys, monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    _, out, _ = run(["--help"], capsys)
    assert "\x1b[7;1;36m" in out  # cyan section pill
    assert "\x1b[38;5;196m" in out  # first rainbow stop
    assert "\x1b[7;1;32m" in out  # green version pill


def test_no_color_strips_help_styling(capsys, monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("NO_COLOR", "1")
    _, out, _ = run(["--help"], capsys)
    assert ANSI not in out


def test_version_flag_renders_the_green_pill(capsys, monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    code, out, _ = run(["--version"], capsys)
    assert code == 0
    assert "\x1b[7;1;32m" in out  # same green pill as the help banner
    assert f"deslopper v{__version__}" in out


def test_version_flag_piped_is_plain(capsys, monkeypatch):
    monkeypatch.delenv("FORCE_COLOR", raising=False)
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
    assert "  Lint files and fail on findings." in out
