"""Terminal vocabulary: the icons, the wordmark's colour stops, the width, word wrap,
and the one-line status messages.

The look is VerBump's (github.com/jv-k/verbump): the same icons and the same rainbow
stops. Styling itself is gum's job (gum.py, ADR 0002); this module only names things.
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

# VerBump's 7-stop 256-colour ramp, stretched to one stop per wordmark letter.
RAINBOW_STOPS = (196, 202, 214, 226, 82, 39, 21, 93, 163)


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
