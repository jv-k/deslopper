"""Terminal styling: the colour gate, the icon vocabulary, pills, and log lines.

The look is VerBump's (github.com/jv-k/verbump): the same icons, the same
inverted-video pill headers, and the same colour-gate precedence. Every style
lives on a Palette; when the gate is off every sequence is the empty string, so
styled and plain output share one code path and piped bytes match today's.
"""

import os
import sys

I_OK = "✔"
I_WARN = "!"
I_ERROR = "✖"
I_INFO = "ℹ"
I_BULLET = "•"
I_ARROW = "→"
I_TRACE = "↳"

# VerBump's 7-stop 256-colour ramp, stretched to one stop per wordmark letter.
RAINBOW_STOPS = (196, 202, 214, 226, 82, 39, 21, 93, 163)


def color_enabled(stream=None) -> bool:
    """The gate, in VerBump's precedence: NO_COLOR off, force-vars on, TTY on."""
    if os.environ.get("NO_COLOR"):
        return False
    for var in ("CLICOLOR_FORCE", "FORCE_COLOR"):
        value = os.environ.get(var)
        if value and value != "0":
            return True
    stream = sys.stdout if stream is None else stream
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())


class Palette:
    def __init__(self, enabled: bool):
        def seq(code: str) -> str:
            return code if enabled else ""

        self.enabled = enabled
        self.reset = seq("\033[0m")
        self.bold = seq("\033[1m")
        self.dim = seq("\033[2m")
        self.ok = seq("\033[0;32m")
        self.error = seq("\033[0;31m")
        self.attn = seq("\033[1;33m")
        self.info = seq("\033[0;36m")
        self.bullet = seq("\033[0;35m")
        # A pill is one combined sequence: the standalone fg codes above start
        # with a reset, which would cancel a preceding invert + bold.
        self.hdr_cyan = seq("\033[7;1;36m")
        self.hdr_green = seq("\033[7;1;32m")
        self.hdr_yellow = seq("\033[7;1;33m")
        self.hdr_red = seq("\033[7;1;31m")
        self.hdr_gray = seq("\033[7;2;37m")
        self.rainbow = tuple(seq(f"\033[38;5;{stop}m") for stop in RAINBOW_STOPS)


PLAIN = Palette(False)


def palette(stream=None) -> Palette:
    return Palette(color_enabled(stream))


def pill(pal: Palette, style: str, text: str) -> str:
    return f"{style} {text} {pal.reset}"


def status_line(pal: Palette, style: str, icon: str, message: str) -> str:
    return f"{style}{icon}{pal.reset} {message}"


def trace_line(pal: Palette, message: str) -> str:
    return f"  {pal.dim}{I_TRACE} {message}{pal.reset}"


def log_success(pal, message, stream=None):
    print(status_line(pal, pal.ok, I_OK, message), file=stream or sys.stdout)


def log_warn(pal, message, stream=None):
    print(status_line(pal, pal.attn, I_WARN, message), file=stream or sys.stdout)


def log_error(pal, message, stream=None):
    print(status_line(pal, pal.error, I_ERROR, message), file=stream or sys.stderr)


def log_info(pal, message, stream=None):
    print(status_line(pal, pal.info, I_INFO, message), file=stream or sys.stdout)
