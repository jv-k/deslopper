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
from dataclasses import dataclass

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
    "bullet": "#ab9df2",
}


def _part(style: str, text: str) -> str:
    """One part as a template call. `style` is space-separated tokens: bold, faint, pill
    (accent background), pill-ok (ok background), palette colour names, and 256-colour
    numbers such as 196; "" is plain. A JSON string is a valid Go template string,
    so quotes, backslashes and any template syntax in the text stay literal."""
    call = json.dumps(text, ensure_ascii=False)
    nested = False  # a function call, which needs brackets when another wraps it
    tokens = style.split()
    pills = {"pill": "accent", "pill-ok": "ok"}
    pill = next((t for t in tokens if t in pills), None)
    if pill:
        call = 'Color "%s" "%s" %s' % (PALETTE["on-accent"], PALETTE[pills[pill]], call)
        nested = True
        tokens = ["bold"] + [t for t in tokens if t not in pills and t != "bold"]
    else:
        colours = [PALETTE[t] if t in PALETTE else t for t in tokens
                   if t in PALETTE or t.isdigit()]
        if colours:
            call = 'Color "%s" %s' % (colours[-1], call)
            nested = True
    for token, func in (("faint", "Faint"), ("bold", "Bold")):
        if token in tokens:
            call = "%s (%s)" % (func, call) if nested else "%s %s" % (func, call)
            nested = True
    return "{{ %s }}" % call


# The line render puts before and after a view, for gum to trim instead of the view.
_MARK = "{{ \"|\" }}"


@dataclass
class Table:
    """A bordered table in a view, drawn by gum table. `columns` names the header
    cells, and each row is a list of cells, each a list of (style, text) parts like a
    line's. gum draws the first row in bold, as it draws a selection, so a caller puts
    the row that leads first.

    `width`, when set, is the box's outer width: the columns after the first share
    what the text leaves over. A table whose text is wider keeps its own width."""

    columns: list
    rows: list
    indent: int = 2
    width: int = 0


def _widths(table: Table) -> list:
    """Each column's text width, widened so the box is `table.width` across. Each
    column adds a space either side and a border."""
    grid = [list(table.columns)] + [["".join(t for _s, t in cell) for cell in row]
                                    for row in table.rows]
    widths = [max(len(row[i]) for row in grid) for i in range(len(table.columns))]
    spare = table.width - sum(widths) - 3 * len(widths) - 1
    rest = len(widths) - 1
    if spare > 0 and rest:
        share, extra = divmod(spare, rest)
        for i in range(1, len(widths)):
            widths[i] += share + (i > rest - extra)
    return widths


def _template(line) -> list:
    """A view line as template lines: one for a line of parts, one per row for a table,
    its cells split by tabs."""
    if isinstance(line, Table):
        return ["\t".join("".join(_part(s, t) for s, t in cell) for cell in row)
                for row in line.rows]
    return ["".join(_part(s, t) for s, t in line)]


def _table(table: Table, cells: list):
    """`table` drawn by gum table from its styled rows, indented, or None. gum sizes a
    column to its widest cell and ignores --widths with --print, so padding the header
    names sets the widths."""
    names = [(c or " ").ljust(w) for c, w in zip(table.columns, _widths(table))]
    drawn = _run(["table", "--print", "--separator", "\t", "--columns",
                  ",".join(names), "--border", "rounded",
                  "--border.foreground", PALETTE["rule"], "--lazy-quotes"],
                 "".join(row + "\n" for row in cells))
    if drawn is None:
        return None
    return [" " * table.indent + row for row in drawn.rstrip("\n").split("\n")]


def render(lines):
    """A view, a list of lines of (style, text) parts and tables, drawn by gum, or None
    when gum cannot draw it. One format call styles every line and table cell; each
    table adds one gum table call."""
    templates = [_template(line) for line in lines]
    # gum trims the whitespace around what it draws, blank lines included, which would
    # shift a table's rows. A marker line on each side keeps every line in its place.
    drawn = _run(["format", "--type", "template"], "\n".join(
        [_MARK] + [t for group in templates for t in group] + [_MARK]) + "\n")
    if drawn is None:
        return None
    styled = drawn.split("\n")
    if len(styled) != 2 + sum(len(group) for group in templates):
        return None
    styled = styled[1:-1]
    out = []
    for line, group in zip(lines, templates):
        rows, styled = styled[:len(group)], styled[len(group):]
        if isinstance(line, Table):
            rows = _table(line, rows)
            if rows is None:
                return None
        out += rows
    # Trim the view as gum trims a drawing, so a view looks the same with or without
    # a table, then put back the last newline gum drops.
    return "\n".join(out).strip() + "\n"


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


def _plain_table(table: Table) -> list:
    """`table` as the same rounded box gum draws, in plain text."""
    grid = [list(table.columns)] + [["".join(t for _s, t in cell) for cell in row]
                                    for row in table.rows]
    widths = _widths(table)

    def edge(left, mid, right):
        return left + mid.join("─" * (w + 2) for w in widths) + right

    def row(cells):
        return "│" + "│".join(f" {c.ljust(w)} " for c, w in zip(cells, widths)) + "│"

    out = [edge("╭", "┬", "╮"), row(grid[0]), edge("├", "┼", "┤")]
    out += [row(cells) for cells in grid[1:]] + [edge("╰", "┴", "╯")]
    return [" " * table.indent + line for line in out]


def plain(lines) -> str:
    """A view as plain text: every part's text, no styling, and each table as a box."""
    out = []
    for line in lines:
        if isinstance(line, Table):
            out += _plain_table(line)
        else:
            out.append("".join(text for _style, text in line))
    return "".join(line + "\n" for line in out)


def write(lines, stream=None) -> None:
    """Write a view to `stream`: drawn by gum on an attended run, else as plain text.

    Every styled screen goes through here, so a run without gum, a pipe, or a gum that
    fails all print the same words, unstyled."""
    stream = sys.stdout if stream is None else stream
    drawn = render(lines) if attended(stream) else None
    stream.write(drawn if drawn is not None else plain(lines))
