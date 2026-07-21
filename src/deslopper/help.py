"""The help system: the wordmark banner and VerBump-style section rendering.

The logo IS the wordmark below — figlet's "future" font, pre-rendered to a
literal so the runtime stays standard-library only, one rainbow colour per
letter. Sections are inverted-video pills; option rows are two columns with a
fixed description column and fluid wrapping on a terminal. Piped output keeps a
stable single-line layout (width 0 disables wrapping, the gate strips colour).
"""

import os
import sys

from . import __version__, ui

# figlet "future", one 3-cell chunk per letter of "deslopper".
WORDMARK = (
    ("╺┳┓", "┏━╸", "┏━┓", "╻  ", "┏━┓", "┏━┓", "┏━┓", "┏━╸", "┏━┓"),
    (" ┃┃", "┣╸ ", "┗━┓", "┃  ", "┃ ┃", "┣━┛", "┣━┛", "┣╸ ", "┣┳┛"),
    ("╺┻┛", "┗━╸", "┗━┛", "┗━╸", "┗━┛", "╹  ", "╹  ", "┗━╸", "╹┗╸"),
)

AUTHOR = "John Valai"
HOMEPAGE = "https://github.com/jv-k/deslopper"
TAGLINE = (
    "A deterministic prose linter for the mechanical tells of "
    "machine-generated writing."
)

# Label column for option/command/example rows, VerBump's OPT_COL pattern:
# a label that reaches the column stacks instead of crowding the description.
OPT_COL = 30

# One entry per subcommand: the synopsis after "deslopper <name>", the
# description, the option rows (short, long, arg, description), and examples.
COMMANDS = {
    "lint": {
        "synopsis": "[paths...] [options]",
        "description": "Lint files and fail on findings.",
        "options": [
            ("", "--strict", "", "Fail on warn-tier findings too."),
            ("", "--config", "<file>", "Use this config file instead of discovering one."),
            ("", "--format", "<fmt>", "Output format: text (default), github, or json."),
        ],
        "examples": [
            ("deslopper lint", "Lint the configured include set."),
            ("deslopper lint docs/ README.md", "Lint specific paths."),
            ("deslopper lint --strict", "Fail on warn-tier findings too."),
            ("deslopper lint --format github", "Emit GitHub Actions annotations."),
        ],
    },
    "check": {
        "synopsis": "[paths...] [options]",
        "description": "Report findings, always exit 0.",
        "options": [
            ("", "--config", "<file>", "Use this config file instead of discovering one."),
        ],
        "examples": [
            ("deslopper check", "See the findings without failing the run."),
        ],
    },
    "rules": {
        "synopsis": "[options]",
        "description": "List the active tells.",
        "options": [
            ("", "--config", "<file>", "Use this config file instead of discovering one."),
            ("", "--format", "<fmt>", "Output format: text (default) or json."),
        ],
        "examples": [
            ("deslopper rules", "List every active tell with tier, phase, and scope."),
        ],
    },
    "init": {
        "synopsis": "[options]",
        "description": "Write a starter config.",
        "options": [
            ("", "--force", "", "Overwrite an existing config."),
        ],
        "examples": [
            ("deslopper init", "Write deslopper.config.json extending the recommended preset."),
        ],
    },
    "eval": {
        "synopsis": "<command> [options]",
        "description": "Judge a rewrite command against the slop fixtures.",
        "options": [
            ("", "--keep", "", "Leave the sandbox on disk and print its path."),
        ],
        "examples": [
            ("deslopper eval 'my-rewriter {dir}'", "Seed a sandbox, rewrite it, judge the result."),
        ],
    },
}


def _term_cols(stream) -> int:
    """Wrap width: 0 (no wrapping) unless the stream is a terminal."""
    isatty = getattr(stream, "isatty", None)
    if not (isatty and isatty()):
        return 0
    cols = os.environ.get("COLUMNS", "")
    if cols.isdigit() and int(cols) > 0:
        return int(cols)
    try:
        return os.get_terminal_size(stream.fileno()).columns
    except (OSError, ValueError):
        return 80


def _wrap(width: int, text: str) -> list:
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


class _Renderer:
    def __init__(self, stream, pal):
        self.stream = stream
        self.pal = pal
        self.cols = _term_cols(stream)

    def line(self, text=""):
        print(text, file=self.stream)

    def pill(self, text, style=None):
        pal = self.pal
        self.line()
        self.line(ui.pill(pal, style or pal.hdr_cyan, text))

    def _desc_width(self) -> int:
        avail = self.cols - OPT_COL
        return avail if avail >= 20 else 20

    def row(self, label_plain, label_styled, desc, dim=False):
        """A two-column row: label, description at OPT_COL, wrapped and hung."""
        pal = self.pal
        if dim:
            desc_open, desc_close = pal.dim, pal.reset
        else:
            desc_open = desc_close = ""
        if len(label_plain) >= OPT_COL:
            self.line(label_styled)
            for wline in self._flow(desc):
                self.line(f"{' ' * OPT_COL}{desc_open}{wline}{desc_close}")
            return
        pad = " " * (OPT_COL - len(label_plain))
        flowed = self._flow(desc)
        first = flowed[0] if flowed else ""
        self.line(f"{label_styled}{pad}{desc_open}{first}{desc_close}")
        for wline in flowed[1:]:
            self.line(f"{' ' * OPT_COL}{desc_open}{wline}{desc_close}")

    def _flow(self, desc) -> list:
        if not desc:
            return []
        if self.cols <= 0:
            return [desc]
        return _wrap(self._desc_width(), desc)

    def prose(self, text, indent=2):
        """Dim wrapped prose (the tagline)."""
        pal = self.pal
        width = self.cols - indent if self.cols > 0 else 0
        lines = _wrap(width, text) if width > 0 else [text]
        for wline in lines:
            self.line(f"{' ' * indent}{pal.dim}{wline}{pal.reset}")


def _option_row(rend, short, long, arg, desc, dim=False):
    pal = rend.pal
    if short:
        plain = f"  {short}, {long}"
        styled = f"  {pal.dim}{short}{pal.reset}, {pal.bold}{long}{pal.reset}"
    else:
        # Align long-only flags under the long column: gutter + "-x, " = 6.
        plain = f"      {long}"
        styled = f"      {pal.bold}{long}{pal.reset}"
    if arg:
        plain += f" {arg}"
        styled += f" {arg}"
    rend.row(plain, styled, desc, dim=dim)


def _example_row(rend, command, desc):
    pal = rend.pal
    plain = f"  {command}"
    styled = f"  {pal.dim}{command}{pal.reset}"
    rend.row(plain, styled, desc, dim=True)


def _banner(rend):
    pal = rend.pal
    for row in WORDMARK:
        chunks = [f"{colour}{chunk}" for colour, chunk in zip(pal.rainbow, row)]
        rend.line("".join(chunks) + pal.reset)
    rend.line()
    rend.line(ui.pill(pal, pal.hdr_green, f"deslopper v{__version__}"))
    rend.line(f" {pal.bullet}{ui.I_BULLET}{pal.reset} Author:   {AUTHOR}")
    rend.line(f" {pal.bullet}{ui.I_BULLET}{pal.reset} Homepage: {HOMEPAGE}")
    rend.line()
    rend.prose(TAGLINE)


def render_root(stream=None, pal=None):
    stream = stream or sys.stdout
    rend = _Renderer(stream, pal or ui.palette(stream))
    _banner(rend)

    rend.pill("USAGE")
    rend.line(f"  {rend.pal.bold}deslopper{rend.pal.reset} <command> [options]")

    rend.pill("COMMANDS")
    for name, spec in COMMANDS.items():
        hint = spec["synopsis"].replace("[options]", "").strip()
        plain = f"  {name}" + (f" {hint}" if hint else "")
        styled = f"  {rend.pal.bold}{name}{rend.pal.reset}" + (
            f" {rend.pal.dim}{hint}{rend.pal.reset}" if hint else ""
        )
        rend.row(plain, styled, spec["description"])

    rend.pill("OPTIONS")
    _option_row(rend, "-h", "--help", "", "Show this help message.")
    _option_row(rend, "", "--version", "", "Print the tool version and exit.")

    rend.pill("EXAMPLES")
    _example_row(rend, "deslopper lint", "Lint the configured include set.")
    _example_row(rend, "deslopper lint --strict", "Fail on warn-tier findings too.")
    _example_row(rend, "deslopper rules", "List the active tells.")
    _example_row(rend, "deslopper init", "Write a starter config.")

    rend.line()
    rend.prose("(run 'deslopper <command> --help' for that command's options)")
    rend.line()


def render_command(name, stream=None, pal=None):
    stream = stream or sys.stdout
    rend = _Renderer(stream, pal or ui.palette(stream))
    pal = rend.pal
    spec = COMMANDS[name]

    rend.line()
    rend.line(ui.pill(pal, pal.hdr_green, f"deslopper {name}"))
    rend.prose(spec["description"])

    rend.pill("USAGE")
    rend.line(f"  {pal.bold}deslopper {name}{pal.reset} {spec['synopsis']}")

    rend.pill("OPTIONS")
    for short, long, arg, desc in spec["options"]:
        _option_row(rend, short, long, arg, desc)
    _option_row(rend, "-h", "--help", "", "Show this help message.")

    if spec["examples"]:
        rend.pill("EXAMPLES")
        for command, desc in spec["examples"]:
            _example_row(rend, command, desc)
    rend.line()


def maybe_help(argv):
    """Intercept -h/--help and the bare invocation before argparse parses.

    Returns an exit code when help was rendered, None to continue parsing.
    Everything after a literal `--` is data, never a help flag.
    """
    visible = []
    for arg in argv:
        if arg == "--":
            break
        visible.append(arg)
    if not argv:
        render_root(sys.stderr)
        return 2
    if visible and visible[0] in ("-h", "--help"):
        render_root(sys.stdout)
        return 0
    if (
        visible
        and visible[0] in COMMANDS
        and any(arg in ("-h", "--help") for arg in visible[1:])
    ):
        render_command(visible[0], sys.stdout)
        return 0
    return None
