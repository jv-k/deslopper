"""The help system: the wordmark banner and VerBump-style section rendering.

The logo IS the wordmark below — figlet's "future" font, pre-rendered to a
literal so the runtime stays standard-library only, one rainbow colour per
letter. Sections are inverted-video pills; option rows are two columns with a
fixed description column, and every layout wraps to the width: COLUMNS wins,
then the terminal's own size, then 80 — so piped output wraps neatly too (the
colour gate still strips styling there).
"""

import sys
from importlib import metadata as importlib_metadata

from . import __version__, ui

# figlet "future", one 3-cell chunk per letter of "deslopper".
WORDMARK = (
    ("╺┳┓", "┏━╸", "┏━┓", "╻  ", "┏━┓", "┏━┓", "┏━┓", "┏━╸", "┏━┓"),
    (" ┃┃", "┣╸ ", "┗━┓", "┃  ", "┃ ┃", "┣━┛", "┣━┛", "┣╸ ", "┣┳┛"),
    ("╺┻┛", "┗━╸", "┗━┛", "┗━╸", "┗━┛", "╹  ", "╹  ", "┗━╸", "╹┗╸"),
)

_AUTHOR = "John Valai"
_HOMEPAGE = "https://github.com/jv-k/deslopper"
_TAGLINE = (
    "A deterministic prose linter for the mechanical tells of "
    "machine-generated writing."
)


def _package_facts():
    """Tagline, author, homepage from the installed package metadata.

    The literals above are fallbacks so the banner never renders a blank field
    (e.g. running from a source tree that was never pip-installed).
    """
    tagline, author, homepage = _TAGLINE, _AUTHOR, _HOMEPAGE
    try:
        meta = importlib_metadata.metadata("deslopper")
    except importlib_metadata.PackageNotFoundError:
        return tagline, author, homepage
    tagline = meta.get("Summary") or tagline
    author = meta.get("Author") or author
    for url in meta.get_all("Project-URL") or []:
        label, _, dest = url.partition(",")
        if label.strip().lower() == "homepage" and dest.strip():
            homepage = dest.strip()
    return tagline, author, homepage

# Label column for option/command/example rows, VerBump's OPT_COL pattern:
# a label that reaches the column stacks instead of crowding the description.
OPT_COL = 30

# One entry per subcommand: the synopsis after "deslopper <name>", the
# description, the option rows (short, long, arg, description), and examples.
# The completion scripts render from this same table, through the extra
# machine-readable keys the help itself ignores: "choices" enumerates a flag's
# values, "paths" marks a file-path positional, and "positional_choices"
# enumerates a positional. A flag whose arg is "<file>" completes as a path.
COMMANDS = {
    "lint": {
        "synopsis": "[paths...] [options]",
        "description": "Lint files and fail on findings.",
        "paths": True,
        "choices": {"--format": ("text", "github", "json")},
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
        "paths": True,
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
        "choices": {"--format": ("text", "json")},
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
    "completions": {
        "synopsis": "[shell] [options]",
        "description": "Print a shell completion script.",
        "positional_choices": ("bash", "zsh", "fish"),
        "options": [],
        "examples": [
            ("deslopper completions", "Print the script for the shell named in $SHELL."),
            ("deslopper completions bash >> ~/.bash_completion", "Install for bash."),
            ("deslopper completions zsh > ~/.zfunc/_deslopper", "Install for zsh, with ~/.zfunc in fpath."),
            ("deslopper completions fish > ~/.config/fish/completions/deslopper.fish", "Install for fish."),
        ],
    },
}


class _Renderer:
    def __init__(self, stream, pal):
        self.stream = stream
        self.pal = pal
        self.cols = ui.term_cols(stream)

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
        # Stack once the label would leave less than the 2-space gutter.
        if len(label_plain) > OPT_COL - 2:
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
        return ui.wrap(self._desc_width(), desc)

    def prose(self, text, indent=2):
        """Dim wrapped prose (the tagline)."""
        pal = self.pal
        width = self.cols - indent
        for wline in ui.wrap(width if width >= 20 else 20, text):
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
    tagline, author, homepage = _package_facts()
    for row in WORDMARK:
        chunks = [f"{colour}{chunk}" for colour, chunk in zip(pal.rainbow, row)]
        rend.line("".join(chunks) + pal.reset)
    rend.line()
    rend.line(ui.pill(pal, pal.hdr_green, f"deslopper v{__version__}"))
    rend.line(f" {pal.bullet}{ui.I_BULLET}{pal.reset} Author:   {author}")
    rend.line(f" {pal.bullet}{ui.I_BULLET}{pal.reset} Homepage: {homepage}")
    rend.line()
    rend.prose(tagline)


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


def render_version(stream=None, pal=None):
    stream = stream or sys.stdout
    pal = pal or ui.palette(stream)
    print(ui.pill(pal, pal.hdr_green, f"deslopper v{__version__}"), file=stream)


def maybe_help(argv):
    """Intercept -h/--help, --version, and the bare invocation before argparse.

    Returns an exit code when a screen was rendered, None to continue parsing.
    Everything after a literal `--` is data, never a help flag.
    """
    visible = []
    for arg in argv:
        if arg == "--":
            break
        visible.append(arg)
    if not visible:
        # Bare `deslopper` (or `deslopper --`): orientation, but still an error.
        render_root(sys.stderr)
        return 2
    if visible and visible[0] in ("-h", "--help"):
        render_root(sys.stdout)
        return 0
    if visible and visible[0] == "--version":
        render_version(sys.stdout)
        return 0
    if (
        visible
        and visible[0] in COMMANDS
        and any(arg in ("-h", "--help") for arg in visible[1:])
    ):
        render_command(visible[0], sys.stdout)
        return 0
    return None
