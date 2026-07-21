"""The completions command, driven through main(argv) with captured stdio."""

import argparse

import pytest

from deslopper import help as help_screen
from deslopper.cli import main, _build_parser

SHELLS = ("bash", "zsh", "fish")
COMMANDS = ("lint", "check", "rules", "init", "eval", "completions")


def run(args, capsys):
    code = main(args)
    out = capsys.readouterr()
    return code, out.out, out.err


@pytest.mark.parametrize("shell", SHELLS)
def test_script_names_every_command(shell, capsys):
    code, out, err = run(["completions", shell], capsys)
    assert code == 0
    for command in COMMANDS:
        assert command in out


@pytest.mark.parametrize("shell", SHELLS)
def test_script_names_every_flag_and_format_value(shell, capsys):
    _, out, _ = run(["completions", shell], capsys)
    for flag in ("strict", "config", "format", "force", "keep"):
        assert flag in out
    for value in ("text", "github", "json"):
        assert value in out


@pytest.mark.parametrize("shell", SHELLS)
def test_format_values_stay_per_command(shell, capsys):
    """Each command completes its own --format set, never a shared superset."""
    _, out, _ = run(["completions", shell], capsys)
    assert "text github json" in out
    assert "text json" in out


def test_each_shell_gets_its_own_dialect(capsys):
    _, bash, _ = run(["completions", "bash"], capsys)
    assert "complete -o filenames -F _deslopper deslopper" in bash
    _, zsh, _ = run(["completions", "zsh"], capsys)
    assert zsh.startswith("#compdef deslopper")
    _, fish, _ = run(["completions", "fish"], capsys)
    assert "complete -c deslopper" in fish


def test_detects_the_shell_from_SHELL(capsys, monkeypatch):
    monkeypatch.setenv("SHELL", "/bin/zsh")
    code, out, _ = run(["completions"], capsys)
    assert code == 0
    assert out.startswith("#compdef deslopper")


def test_missing_SHELL_is_a_usage_error(capsys, monkeypatch):
    monkeypatch.delenv("SHELL", raising=False)
    code, out, err = run(["completions"], capsys)
    assert code == 2
    assert out == ""
    for shell in SHELLS:
        assert shell in err


def test_unsupported_detected_shell_is_a_usage_error(capsys, monkeypatch):
    monkeypatch.setenv("SHELL", "/bin/tcsh")
    code, _, err = run(["completions"], capsys)
    assert code == 2
    assert "tcsh" in err
    for shell in SHELLS:
        assert shell in err


def test_unsupported_explicit_shell_is_a_usage_error(capsys):
    code, out, err = run(["completions", "powershell"], capsys)
    assert code == 2
    assert out == ""
    assert "powershell" in err
    for shell in SHELLS:
        assert shell in err


def test_stdout_is_plain_even_under_forced_color(capsys, monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    _, out, _ = run(["completions", "bash"], capsys)
    assert "\x1b[" not in out


def test_root_help_lists_completions(capsys):
    code, out, _ = run(["--help"], capsys)
    assert code == 0
    assert "completions" in out


def test_command_help_carries_install_guidance(capsys):
    code, out, _ = run(["completions", "--help"], capsys)
    assert code == 0
    for shell in SHELLS:
        assert shell in out


def test_command_table_covers_every_parser_flag():
    """Drift guard: a flag added to the parser must reach the help table,

    because completions and help both render from that table.
    """
    parser = _build_parser()
    sub = next(
        a for a in parser._actions if isinstance(a, argparse._SubParsersAction)
    )
    assert set(sub.choices) == set(help_screen.COMMANDS)
    for name, subparser in sub.choices.items():
        parser_flags = {
            opt
            for action in subparser._actions
            for opt in action.option_strings
        }
        table_flags = {
            long for _short, long, _arg, _desc in help_screen.COMMANDS[name]["options"]
        }
        assert parser_flags == table_flags, name
        parser_choices = {
            opt: tuple(action.choices)
            for action in subparser._actions
            if action.choices and action.option_strings
            for opt in action.option_strings
        }
        table_choices = {
            flag: tuple(values)
            for flag, values in help_screen.COMMANDS[name].get("choices", {}).items()
        }
        assert parser_choices == table_choices, name
