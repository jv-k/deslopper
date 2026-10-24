"""The gum layer: the attended check, the install hint, and the calls themselves.

No test reaches a real gum. The suite starts every test without gum (conftest's
`no_gum`), and `gum_shim` installs a stand-in that records each call.
"""

import io

from deslopper import gum


class Tty(io.StringIO):
    def isatty(self):
        return True


# The attended check reads the same two variables gum does: NO_COLOR and CLICOLOR_FORCE.


def test_no_gum_is_never_attended(monkeypatch):
    monkeypatch.setenv("CLICOLOR_FORCE", "1")
    assert not gum.attended(Tty())


def test_a_terminal_with_gum_is_attended(gum_shim, monkeypatch):
    monkeypatch.delenv("CLICOLOR_FORCE")
    assert gum.attended(Tty())
    assert not gum.attended(io.StringIO())


def test_no_color_turns_a_terminal_unattended(gum_shim, monkeypatch):
    monkeypatch.delenv("CLICOLOR_FORCE")
    monkeypatch.setenv("NO_COLOR", "1")
    assert not gum.attended(Tty())


def test_clicolor_force_attends_without_a_terminal(gum_shim):
    assert gum.attended(io.StringIO())


def test_clicolor_force_zero_does_not_force(gum_shim, monkeypatch):
    monkeypatch.setenv("CLICOLOR_FORCE", "0")
    assert not gum.attended(io.StringIO())


# Without gum, a terminal gets one line naming the install, once per run.


def test_hint_names_the_install_once_on_a_terminal(capsys):
    gum.hint(Tty())
    gum.hint(Tty())
    assert capsys.readouterr().err == gum.HINT + "\n"
    assert "brew install gum" in gum.HINT


def test_no_hint_off_a_terminal_or_under_no_color(capsys, monkeypatch):
    gum.hint(io.StringIO())
    monkeypatch.setenv("NO_COLOR", "1")
    gum.hint(Tty())
    assert capsys.readouterr().err == ""


def test_no_hint_when_gum_is_installed(gum_shim, capsys):
    gum.hint(Tty())
    assert capsys.readouterr().err == ""


# The calls. Each returns gum's output for the caller to write, and forces colour on,
# because gum writes into a pipe here and would otherwise drop its own styling.


def test_render_sends_one_template_with_each_part_styled(gum_shim):
    out = gum.render([[("bold", "a.md")], [], [("", "  "), ("error", "✖ error")]])
    call = gum_shim()[0]
    assert call["args"] == ["format", "--type", "template"]
    assert call["stdin"] == ('{{ Bold "a.md" }}\n\n{{ "  " }}'
                             '{{ Color "%s" "✖ error" }}\n' % gum.PALETTE["error"])
    assert call["clicolor_force"] == "1"
    # gum drops the last newline; render puts it back.
    assert out.endswith("\n")


def test_render_combines_style_tokens():
    accent = gum.PALETTE["accent"]
    assert gum._part("bold accent", "a.md") == '{{ Bold (Color "%s" "a.md") }}' % accent
    assert gum._part("faint", "x") == '{{ Faint "x" }}'
    assert gum._part("pill", " deslopper ") == \
        '{{ Bold (Color "%s" "%s" " deslopper ") }}' % (gum.PALETTE["on-accent"], accent)


def test_render_keeps_template_syntax_in_the_text_literal(gum_shim):
    gum.render([[("faint", 'say "{{ .X }}" \\ here')]])
    assert gum_shim()[0]["stdin"] == '{{ Faint "say \\"{{ .X }}\\" \\\\ here" }}\n'


def test_spin_runs_a_spinner_for_the_block_and_stops_it(gum_shim):
    import time

    with gum.spin("Asking Jev about 2 findings in a.md"):
        # The spinner is a separate process; wait for it to start, as real work would.
        deadline = time.monotonic() + 5
        while not gum_shim() and time.monotonic() < deadline:
            time.sleep(0.02)
    args = gum_shim()[0]["args"]
    assert args[0] == "spin"
    assert args[args.index("--title") + 1] == "Asking Jev about 2 findings in a.md"


def test_spin_leaves_no_process_behind(gum_shim):
    # gum runs a waiting command under the spinner. Stopping gum alone orphans that
    # command, which then holds the terminal or a pipe open after deslopper exits.
    import os
    import time

    pids_file = os.environ["GUM_SHIM_LOG"] + ".pids"
    with gum.spin("waiting"):
        deadline = time.monotonic() + 5
        while not os.path.exists(pids_file) and time.monotonic() < deadline:
            time.sleep(0.02)
    child = int(open(pids_file, encoding="utf-8").read().split()[0])
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            os.kill(child, 0)
        except ProcessLookupError:
            return
        time.sleep(0.02)
    os.kill(child, 9)
    raise AssertionError("the command under the spinner outlived it")


def test_spin_without_gum_just_runs_the_block():
    ran = []
    with gum.spin("unused"):
        ran.append(True)
    assert ran == [True]


# gum is optional, so a gum that fails must never cost the run its output.


def test_render_returns_none_when_gum_fails(gum_shim, monkeypatch):
    monkeypatch.setenv("GUM_SHIM_FAIL", "1")
    assert gum.render([[("bold", "a.md")]]) is None


def test_render_returns_none_when_gum_has_vanished(monkeypatch):
    monkeypatch.setattr(gum, "binary", lambda: "/nonexistent/gum")
    assert gum.render([[("bold", "a.md")]]) is None


def test_spin_runs_the_block_when_gum_cannot_start(monkeypatch):
    monkeypatch.setattr(gum, "binary", lambda: "/nonexistent/gum")
    ran = []
    with gum.spin("Asking Jev"):
        ran.append(True)
    assert ran == [True]
