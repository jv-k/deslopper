"""The deslopper command-line interface."""

import argparse
import json
import os
import sys

from .config import (
    load_config, DEFAULT_INCLUDE, CONFIG_NAME, RECOMMENDED,
)
from .discovery import resolve_worklist
from .engine import lint_files
from .errors import ConfigError, UsageError
from .evaluate import run_eval
from .jev import JevUnavailable, require_key
from . import cache, completions
from . import help as help_screen
from . import gum, report, triage, ui, update

STARTER = {
    "extends": [RECOMMENDED],
    "files": {"include": DEFAULT_INCLUDE, "exclude": []},
}


def _build_parser():
    # add_help=False everywhere: -h/--help and --version are intercepted by
    # help.maybe_help before parsing, so argparse's stock output can never render.
    parser = argparse.ArgumentParser(prog="deslopper", add_help=False)
    sub = parser.add_subparsers(dest="command", required=True)

    # Command descriptions live once, on the help screen's table.
    def command(name):
        return sub.add_parser(
            name, help=help_screen.COMMANDS[name]["description"], add_help=False
        )

    lint = command("lint")
    lint.add_argument("paths", nargs="*")
    lint.add_argument("--strict", action="store_true")
    lint.add_argument("--config")
    # --format choices come from the help table, the single source the
    # completion scripts also render from.
    lint.add_argument("--format", default="text",
                      choices=list(help_screen.COMMANDS["lint"]["choices"]["--format"]))
    # A flag and never a config key, so no repo can switch on network calls for
    # everyone who lints in it. --triage is the name it shipped under, kept as a
    # hidden alias so configs written before the rename still run.
    lint.add_argument("--jev", "--triage", dest="jev", action="store_true")
    lint.add_argument("--no-cache", action="store_true")

    check = command("check")
    check.add_argument("paths", nargs="*")
    check.add_argument("--config")

    rules = command("rules")
    rules.add_argument("--config")
    rules.add_argument("--format", default="text",
                       choices=list(help_screen.COMMANDS["rules"]["choices"]["--format"]))

    init = command("init")
    init.add_argument("--force", action="store_true")

    ev = command("eval")
    ev.add_argument("rewrite_command", metavar="command",
                    help="shell command under test; {dir} receives the sandbox path")
    ev.add_argument("--keep", action="store_true",
                    help="leave the sandbox on disk and print its path")
    ev.add_argument("--plainness", action="store_true",
                    help="also score plainness with Jev, reported never gated")

    comp = command("completions")
    # nargs="?" without choices: an unknown shell goes through UsageError for
    # the same styled error path as every other usage mistake.
    comp.add_argument("shell", nargs="?")

    upd = command("update")
    upd.add_argument("--dry-run", action="store_true")
    return parser


def _lint_command(args):
    cfg, config_path = load_config(getattr(args, "config", None), os.getcwd())
    items = resolve_worklist(args.paths, config_path or None, os.getcwd(), cfg.include, cfg.exclude)
    result = lint_files(items, cfg.tells)
    return cfg, result, items


def _jev_spinner(path, count, index, total):
    noun = "finding" if count == 1 else "findings"
    return gum.spin(f"({index}/{total}) Asking Jev about {count} {noun} in {path}")


def _view(result, sources, items, strict, command, judged=None) -> bool:
    """The attended run's whole output: one view, drawn by gum, on stdout. False when gum
    could not draw it, so the caller prints the plain output instead."""
    lines = report.lint_view(result, sources, len(items), ui.term_cols(), judged=judged,
                             strict=strict, command=command)
    return _draw(lines)


def _draw(lines) -> bool:
    """Write a gum view, or return False when gum could not draw it."""
    drawn = gum.render(lines)
    if drawn is None:
        return False
    sys.stdout.write(drawn)
    return True


def _finish(result, strict, judged=None):
    """The plain run's ending: the unreadable paths and the summary, on stderr."""
    # The findings go to stdout and the summary to stderr. Flush first, so the summary
    # follows the findings when both streams share one pipe.
    sys.stdout.flush()
    for path in result.unreadable:
        print(f"  {ui.I_TRACE} cannot read {path}", file=sys.stderr)
    print(report.summary_line(result, strict, judged), file=sys.stderr)


def _read_sources(result, items) -> dict:
    """The raw text of each file in `items` that has a finding, by display path.

    Files with no findings are never opened. A file that can no longer be read
    maps to empty text, so its findings still go to Jev, without context.
    """
    flagged = {f.path for f in result.findings}
    sources = {}
    for display, read_path in items:
        if display not in flagged:
            continue
        try:
            with open(read_path, encoding="utf-8", newline="\n") as fh:
                sources[display] = fh.read()
        except OSError:
            sources[display] = ""
    return sources


def _do_lint(args):
    if args.jev:
        # Fail on the missing key before any scan output, so the hint is the
        # whole of what the user sees.
        require_key()
    cfg, result, items = _lint_command(args)
    strict = bool(getattr(args, "strict", False) or cfg.strict)
    # The exit code is taken from the scan before triage, so a verdict can never
    # move it: triage is annotation and the scan stays the gate.
    code = report.exit_code(result, strict)
    # Only the text format is ever styled. github and json are machine contracts.
    attended = args.format == "text" and gum.attended(sys.stdout)
    if args.format == "text" and not attended:
        gum.hint(sys.stdout)
    # Read once: Jev gets the lines around each finding, and the view shows them.
    sources = _read_sources(result, items) if args.jev or attended else {}
    judged = None
    if args.jev:
        store = None if args.no_cache else cache.Store(cache.default_dir("jev"))
        judged = triage.run(result, sources, progress=_jev_spinner if attended else None,
                            cache=store)
        result = judged.result
    if args.format == "json":
        # The payload is the whole output, so a model or a tool reads one stream. It
        # carries the summary, the unreadable paths, and the Jev totals and errors.
        sys.stdout.write(report.format_json(result, judged))
        return code
    if attended and _view(result, sources, items, strict, "lint", judged):
        return code
    for error in judged.errors if judged else ():
        print(f"{ui.I_ERROR} triage skipped {error}", file=sys.stderr)
    if args.format == "github":
        sys.stdout.write(report.format_github(result))
    else:
        sys.stdout.write(report.format_text(result))
    _finish(result, strict, judged)
    return code


def _do_check(args):
    cfg, result, items = _lint_command(args)
    if gum.attended(sys.stdout):
        if _view(result, _read_sources(result, items), items, cfg.strict, "check"):
            return 0
    else:
        gum.hint(sys.stdout)
    sys.stdout.write(report.format_text(result))
    _finish(result, cfg.strict)
    return 0


def _do_rules(args):
    cfg, _ = load_config(getattr(args, "config", None), os.getcwd())
    if args.format == "json":
        payload = [
            {"name": t.name, "tier": t.tier, "phase": t.phase, "scope": t.scope}
            for t in cfg.tells
        ]
        print(json.dumps(payload, indent=2))
    elif cfg.tells:
        # gum's view for eyes; the TSV is the stable machine-side layout, and the
        # fallback when gum is absent or cannot draw.
        attended = gum.attended(sys.stdout)
        if not (attended and _draw(report.rule_lines(cfg.tells, ui.term_cols()))):
            if not attended:
                gum.hint(sys.stdout)
            for t in cfg.tells:
                print(f"{t.name}\t{t.tier}\t{t.phase}\t{t.scope}\t{t.message}")
    return 0


def _do_init(args):
    target = os.path.join(os.getcwd(), CONFIG_NAME)
    if os.path.exists(target) and not args.force:
        raise UsageError(f"{CONFIG_NAME} already exists; pass --force to overwrite")
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(STARTER, fh, indent=2)
        fh.write("\n")
    ui.log_success(f"wrote {CONFIG_NAME}")
    return 0


def _do_eval(args):
    return run_eval(args.rewrite_command, keep=args.keep, plainness=args.plainness)


def _do_completions(args):
    sys.stdout.write(completions.script(args.shell or completions.detect()))
    return 0


def _do_update(args):
    return update.run(dry_run=args.dry_run)


_COMMANDS = {
    "lint": _do_lint,
    "check": _do_check,
    "rules": _do_rules,
    "init": _do_init,
    "eval": _do_eval,
    "completions": _do_completions,
    "update": _do_update,
}


def main(argv=None) -> int:
    argv = list(sys.argv[1:]) if argv is None else list(argv)
    helped = help_screen.maybe_help(argv)
    if helped is not None:
        return helped
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return _COMMANDS[args.command](args)
    except (ConfigError, UsageError, JevUnavailable) as exc:
        ui.log_error(str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
