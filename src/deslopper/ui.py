"""Terminal vocabulary: the icons, the wordmark's gradient, the width, word wrap,
and the one-line status messages.

The icons are VerBump's (github.com/jv-k/verbump), and the wordmark's gradient runs
across Monokai Pro's yellow, green and cyan. Styling itself is gum's job (gum.py, ADR 0002); this module only names things.
"""

import os
import sys

from . import gum

I_OK = "✔"
I_WARN = "!"
I_ERROR = "✖"
I_INFO = "ℹ"
I_BULLET = "•"
I_TRACE = "↳"

# The wordmark gradient's three stops: Monokai Pro's yellow, green and cyan, the
# palette the README's screenshots use.
GRADIENT_STOPS = ((255, 216, 102), (169, 220, 118), (120, 220, 232))

# How many columns each row's gradient starts to the right of the row above, which
# tilts the gradient into a diagonal.
GRADIENT_SHIFT = 2


def _blend(t: float) -> str:
    """The colour at `t`, from 0 at the first stop to 1 at the last, as #rrggbb."""
    at = t * (len(GRADIENT_STOPS) - 1)
    i = min(int(at), len(GRADIENT_STOPS) - 2)
    pairs = zip(GRADIENT_STOPS[i], GRADIENT_STOPS[i + 1])
    return "#%02x%02x%02x" % tuple(round(a + (b - a) * (at - i)) for a, b in pairs)


def gradient(rows) -> list:
    """Each row of `rows` as (colour, cell) parts on the diagonal gradient. A space
    gets no colour."""
    span = max(len(rows[0]) - 1 + GRADIENT_SHIFT * (len(rows) - 1), 1)
    return [[("" if cell == " " else _blend((x + GRADIENT_SHIFT * y) / span), cell)
             for x, cell in enumerate(row)] for y, row in enumerate(rows)]


def term_cols(stream=None) -> int:
    """Wrap width, always positive: COLUMNS, then the terminal's size, then 80."""
    cols = os.environ.get("COLUMNS", "")
    if cols.isdigit() and int(cols) > 0:
        return int(cols)
    stream = sys.stdout if stream is None else stream
    isatty = getattr(stream, "isatty", None)
    if isatty and isatty():
        # The stream is a terminal, so its own fd answers and works off POSIX
        # too; the controlling terminal is the fallback for odd redirections.
        try:
            return os.get_terminal_size(stream.fileno()).columns
        except (OSError, ValueError):
            pass
        try:
            with open("/dev/tty") as tty:
                return os.get_terminal_size(tty.fileno()).columns
        except (OSError, ValueError):
            pass
    return 80


def wrap(width: int, text: str) -> list:
    """Greedy word wrap; a word longer than width overflows its own line."""
    lines, line = [], ""
    for word in text.split():
        if not line:
            line = word
        elif len(line) + 1 + len(word) <= width:
            line += " " + word
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _status(style: str, icon: str, message: str, stream) -> None:
    gum.write([[(style, icon), ("", f" {message}")]], stream)


def log_success(message, stream=None):
    _status("ok", I_OK, message, stream or sys.stdout)


def log_error(message, stream=None):
    _status("error", I_ERROR, message, stream or sys.stderr)


def log_info(message, stream=None):
    _status("accent", I_INFO, message, stream or sys.stdout)
