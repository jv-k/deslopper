"""The styled layer over the plain output, drawn by Charm's gum.

An attended run is gum on PATH and either a terminal with NO_COLOR unset, or
CLICOLOR_FORCE set to something other than 0. gum reads those two and never
FORCE_COLOR, so the check reads the same two. On any other run nothing here calls
gum, and the plain output is the whole output. gum is never a dependency: a terminal
without it gets the plain output and one install hint.

Every gum call goes through this module. Each call returns what gum drew, for the
caller to write, except `spin`, which draws on the terminal while a block runs.
"""

import json
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager

HINT = "styled output needs gum (brew install gum)"

_hinted = False


def binary():
    """The gum on PATH, or None. Tests replace this to install a shim or hide gum."""
    return shutil.which("gum")


def _forced() -> bool:
    value = os.environ.get("CLICOLOR_FORCE", "")
    return bool(value) and value != "0"


def _isatty(stream) -> bool:
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())


def attended(stream=None) -> bool:
    if not binary():
        return False
    if _forced():
        return True
    return not os.environ.get("NO_COLOR") and _isatty(sys.stdout if stream is None else stream)


def hint(stream=None) -> None:
    """One stderr line naming the install, when a terminal has no gum. Once per run."""
    global _hinted
    if _hinted or binary() or os.environ.get("NO_COLOR"):
        return
    if not (_isatty(sys.stdout if stream is None else stream) or _forced()):
        return
    _hinted = True
    print(HINT, file=sys.stderr)


def _env() -> dict:
    # gum draws into a pipe here and would drop its colours, so force them on.
    return {**os.environ, "CLICOLOR_FORCE": "1"}


# A view renders in well under a second; a gum that takes this long is stuck.
_TIMEOUT_SECONDS = 30


def _run(args, stdin=None):
    """What gum drew, or None when gum is missing, fails, or hangs. gum is optional, so
    a caller that gets None falls back to the plain output."""
    exe = binary()
    if exe is None:
        return None
    try:
        done = subprocess.run([exe, *args], input=stdin, capture_output=True, text=True,
                              env=_env(), check=False, timeout=_TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    return done.stdout


# The palette a view's colour tokens name. "on-accent" is the text colour on a pill.
PALETTE = {
    "accent": "#87afff",
    "on-accent": "#1c1c1c",
    "error": "#ff5f87",
    "warn": "#ffaf5f",
    "ok": "#87d787",
    "muted": "#8a8a8a",
    "rule": "#444444",
}


def _part(style: str, text: str) -> str:
    """One part as a template call. `style` is space-separated tokens: bold, faint, pill,
    and palette colour names; "" is plain. A JSON string is a valid Go template string,
    so quotes, backslashes and any template syntax in the text stay literal."""
    call = json.dumps(text, ensure_ascii=False)
    nested = False  # a function call, which needs brackets when another wraps it
    tokens = style.split()
    if "pill" in tokens:
        call = 'Color "%s" "%s" %s' % (PALETTE["on-accent"], PALETTE["accent"], call)
        nested = True
        tokens = ["bold"] + [t for t in tokens if t not in ("pill", "bold")]
    else:
        colours = [t for t in tokens if t in PALETTE]
        if colours:
            call = 'Color "%s" %s' % (PALETTE[colours[-1]], call)
            nested = True
    for token, func in (("faint", "Faint"), ("bold", "Bold")):
        if token in tokens:
            call = "%s (%s)" % (func, call) if nested else "%s %s" % (func, call)
            nested = True
    return "{{ %s }}" % call


def render(lines):
    """A view, a list of lines of (style, text) parts, drawn by gum in one call, or None
    when gum cannot draw it."""
    template = "\n".join("".join(_part(s, t) for s, t in line) for line in lines) + "\n"
    drawn = _run(["format", "--type", "template"], template)
    if drawn is None:
        return None
    # gum drops the last newline, so put it back.
    return drawn.rstrip("\n") + "\n"


@contextmanager
def spin(title, stream=None):
    """A spinner on the terminal while the block runs. Without gum the block just runs.

    gum spin wraps a command, but the work here is Python, so the spinner wraps a
    command that waits, and stops when the block ends. Its title cannot change while it
    runs, so a caller starts one spinner per step."""
    exe = binary()
    if not exe:
        yield
        return
    stream = sys.stderr if stream is None else stream
    try:
        target = stream.fileno()
    except (AttributeError, OSError, ValueError):
        target = subprocess.DEVNULL
    # The waiting command ends itself once gum, its parent, is gone. Stopping gum alone
    # would otherwise orphan it, and an orphan keeps the terminal or a pipe open.
    try:
        spinner = subprocess.Popen(
            [exe, "spin", "--spinner", "dot", "--title", title, "--",
             "sh", "-c", "while kill -0 $PPID 2>/dev/null; do sleep 0.2; done"],
            stdin=subprocess.DEVNULL, stdout=target, stderr=target, env=_env(),
        )
    except OSError:
        # gum went missing or cannot start: run the work without a spinner.
        yield
        return
    try:
        yield
    finally:
        spinner.terminate()
        try:
            spinner.wait(timeout=2)
        except subprocess.TimeoutExpired:
            spinner.kill()
            spinner.wait()
