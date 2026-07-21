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
from . import completions
from . import help as help_screen
from . import report, ui

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

    comp = command("completions")
    # nargs="?" without choices: an unknown shell goes through UsageError for
    # the same styled error path as every other usage mistake.
    comp.add_argument("shell", nargs="?")
    return parser


def _lint_command(args):
    cfg, config_path = load_config(getattr(args, "config", None), os.getcwd())
    items = resolve_worklist(args.paths, config_path or None, os.getcwd(), cfg.include, cfg.exclude)
    result = lint_files(items, cfg.tells)
    return cfg, result


def _emit(result, fmt, pal):
    # Only the text format is ever styled; github and json are machine contracts.
    if fmt == "text":
        sys.stdout.write(report.format_text(result, pal))
    elif fmt == "github":
        sys.stdout.write(report.format_github(result))
    elif fmt == "json":
        sys.stdout.write(report.format_json(result))


def _finish(result, strict, pal):
    for path in result.unreadable:
        print(ui.trace_line(pal, f"cannot read {path}"), file=sys.stderr)
    print(report.summary_line(result, strict, pal), file=sys.stderr)


def _do_lint(args, pal):
    cfg, result = _lint_command(args)
    strict = bool(getattr(args, "strict", False) or cfg.strict)
    _emit(result, args.format, pal)
    _finish(result, strict, pal)
    return report.exit_code(result, strict)


def _do_check(args, pal):
    cfg, result = _lint_command(args)
    sys.stdout.write(report.format_text(result, pal))
    _finish(result, cfg.strict, pal)
    return 0


def _do_rules(args, pal):
    cfg, _ = load_config(getattr(args, "config", None), os.getcwd())
    if args.format == "json":
        payload = [
            {"name": t.name, "tier": t.tier, "phase": t.phase, "scope": t.scope}
            for t in cfg.tells
        ]
        print(json.dumps(payload, indent=2))
    elif pal.enabled and cfg.tells:
        # Aligned, tier-coloured columns for eyes; the piped TSV below is the
        # stable machine-side layout. The message column wraps to the terminal
        # and hangs under itself, like the help.
        name_w = max(len(t.name) for t in cfg.tells)
        msg_col = 2 + name_w + 2 + 5 + 2 + 11 + 1 + 5 + 2
        avail = ui.term_cols() - msg_col
        if avail < 20:
            avail = 20
        for t in cfg.tells:
            lines = ui.wrap(avail, t.message) or [""]
            print(
                f"  {pal.bold}{t.name:<{name_w}}{pal.reset}  "
                f"{report.tier_style(pal, t.tier)}{t.tier:<5}{pal.reset}  "
                f"{pal.dim}{t.phase:<11} {t.scope:<5}{pal.reset}  {lines[0]}"
            )
            for cont in lines[1:]:
                print(f"{' ' * msg_col}{cont}")
    else:
        for t in cfg.tells:
            print(f"{t.name}\t{t.tier}\t{t.phase}\t{t.scope}\t{t.message}")
    return 0


def _do_init(args, pal):
    target = os.path.join(os.getcwd(), CONFIG_NAME)
    if os.path.exists(target) and not args.force:
        raise UsageError(f"{CONFIG_NAME} already exists; pass --force to overwrite")
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(STARTER, fh, indent=2)
        fh.write("\n")
    ui.log_success(pal, f"wrote {CONFIG_NAME}")
    return 0


def _do_eval(args, pal):
    return run_eval(args.rewrite_command, keep=args.keep, pal=pal)


def _do_completions(args, pal):
    sys.stdout.write(completions.script(args.shell or completions.detect()))
    return 0


_COMMANDS = {
    "lint": _do_lint,
    "check": _do_check,
    "rules": _do_rules,
    "init": _do_init,
    "eval": _do_eval,
    "completions": _do_completions,
}


def main(argv=None) -> int:
    argv = list(sys.argv[1:]) if argv is None else list(argv)
    helped = help_screen.maybe_help(argv)
    if helped is not None:
        return helped
    parser = _build_parser()
    args = parser.parse_args(argv)
    pal = ui.palette()
    try:
        return _COMMANDS[args.command](args, pal)
    except (ConfigError, UsageError) as exc:
        ui.log_error(pal, str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
