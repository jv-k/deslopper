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

from . import __version__, gum, ui

# figlet "future", one 3-cell chunk per letter of "deslopper".
WORDMARK = (
    ("╺┳┓", "┏━╸", "┏━┓", "╻  ", "┏━┓", "┏━┓", "┏━┓", "┏━╸", "┏━┓"),
    (" ┃┃", "┣╸ ", "┗━┓", "┃  ", "┃ ┃", "┣━┛", "┣━┛", "┣╸ ", "┣┳┛"),
    ("╺┻┛", "┗━╸", "┗━┛", "┗━╸", "┗━┛", "╹  ", "╹  ", "┗━╸", "╹┗╸"),
)

_AUTHOR = "John Valai"
_HOMEPAGE = "https://github.com/jv-k/deslopper"
_TAGLINE = (
    "A deterministic slop linter for Markdown: it finds the mechanical tells "
    "of machine-generated writing."
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
# "hidden" lists parser flags that neither the help nor the completions show.
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
            ("", "--jev", "", "Ask Jev to mark each finding keep or rewrite. Needs AI_GATEWAY_API_KEY."),
            ("", "--no-cache", "", "With --jev, ask again about findings Jev answered before."),
        ],
        # --triage is the old name of --jev.
        "hidden": ("--triage",),
        "examples": [
            ("deslopper lint", "Lint the configured include set."),
            ("deslopper lint docs/ README.md", "Lint specific paths."),
            ("deslopper lint --strict", "Fail on warn-tier findings too."),
            ("deslopper lint --format github", "Emit GitHub Actions annotations."),
            ("deslopper lint --jev docs/", "Sort the findings into keep and rewrite."),
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
            ("", "--plainness", "", "Also score plainness with Jev (needs AI_GATEWAY_API_KEY). Reported, never gated."),
        ],
        "examples": [
            ("deslopper eval 'my-rewriter {dir}'", "Seed a sandbox, rewrite it, judge the result."),
            ("deslopper eval --plainness 'my-rewriter {dir}'", "The same, with a plainness score per fixture."),
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
    """Collects a help screen as lines of (style, text) parts; gum.write draws it."""

    def __init__(self, stream):
        self.stream = stream
        self.cols = ui.term_cols(stream)
        self.lines = []

    def line(self, *parts):
        self.lines.append([p if isinstance(p, tuple) else ("", p) for p in parts])

    def pill(self, text, style="pill"):
        self.line()
        self.line((style, f" {text} "))

    def _desc_width(self) -> int:
        avail = self.cols - OPT_COL
        return avail if avail >= 20 else 20

    def row(self, label, desc, dim=False):
        """A two-column row: label parts, description at OPT_COL, wrapped and hung."""
        width = sum(len(text) for _style, text in label)
        style = "faint" if dim else ""
        flowed = self._flow(desc)
        # Stack once the label would leave less than the 2-space gutter.
        if width > OPT_COL - 2:
            self.line(*label)
            for wline in flowed:
                self.line(" " * OPT_COL, (style, wline))
            return
        first = flowed[0] if flowed else ""
        self.line(*label, " " * (OPT_COL - width), (style, first))
        for wline in flowed[1:]:
            self.line(" " * OPT_COL, (style, wline))

    def _flow(self, desc) -> list:
        if not desc:
            return []
        return ui.wrap(self._desc_width(), desc)

    def prose(self, text, indent=2):
        """Faint wrapped prose (the tagline)."""
        width = self.cols - indent
        for wline in ui.wrap(width if width >= 20 else 20, text):
            self.line(" " * indent, ("faint", wline))

    def done(self):
        gum.write(self.lines, self.stream)


def _option_row(rend, short, long, arg, desc, dim=False):
    if short:
        label = [("", "  "), ("faint", short), ("", ", "), ("bold", long)]
    else:
        # Align long-only flags under the long column: gutter + "-x, " = 6.
        label = [("", "      "), ("bold", long)]
    if arg:
        label.append(("", f" {arg}"))
    rend.row(label, desc, dim=dim)


def _example_row(rend, command, desc):
    rend.row([("", "  "), ("faint", command)], desc, dim=True)


def _banner(rend):
    tagline, author, homepage = _package_facts()
    for row in WORDMARK:
        rend.line(*[(str(stop), chunk) for stop, chunk in zip(ui.RAINBOW_STOPS, row)])
    rend.line()
    rend.line(("pill-ok", f" deslopper v{__version__} "))
    rend.line(" ", ("bullet", ui.I_BULLET), f" Author:   {author}")
    rend.line(" ", ("bullet", ui.I_BULLET), f" Homepage: {homepage}")
    rend.line()
    rend.prose(tagline)


def render_root(stream=None):
    rend = _Renderer(stream or sys.stdout)
    _banner(rend)

    rend.pill("USAGE")
    rend.line("  ", ("bold", "deslopper"), " <command> [options]")

    rend.pill("COMMANDS")
    for name, spec in COMMANDS.items():
        hint = spec["synopsis"].replace("[options]", "").strip()
        label = [("", "  "), ("bold", name)] + ([("faint", f" {hint}")] if hint else [])
        rend.row(label, spec["description"])

    rend.pill("OPTIONS")
    _option_row(rend, "-h", "--help", "", "Show this help message.")
    _option_row(rend, "", "--version", "", "Print the tool version and exit.")

    rend.pill("EXAMPLES")
    _example_row(rend, "deslopper lint", "Lint the configured include set.")
    _example_row(rend, "deslopper lint --strict", "Fail on warn-tier findings too.")
    _example_row(rend, "deslopper lint --jev", "Ask Jev which findings to keep or rewrite.")
    _example_row(rend, "deslopper rules", "List the active tells.")
    _example_row(rend, "deslopper init", "Write a starter config.")

    rend.line()
    rend.prose("(run 'deslopper <command> --help' for that command's options)")
    rend.line()
    rend.done()


def render_command(name, stream=None):
    rend = _Renderer(stream or sys.stdout)
    spec = COMMANDS[name]

    rend.line()
    rend.line(("pill-ok", f" deslopper {name} "))
    rend.prose(spec["description"])

    rend.pill("USAGE")
    rend.line("  ", ("bold", f"deslopper {name}"), f" {spec['synopsis']}")

    rend.pill("OPTIONS")
    for short, long, arg, desc in spec["options"]:
        _option_row(rend, short, long, arg, desc)
    _option_row(rend, "-h", "--help", "", "Show this help message.")

    if spec["examples"]:
        rend.pill("EXAMPLES")
        for command, desc in spec["examples"]:
            _example_row(rend, command, desc)
    rend.line()
    rend.done()


def render_version(stream=None):
    gum.write([[("pill-ok", f" deslopper v{__version__} ")]], stream or sys.stdout)


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
