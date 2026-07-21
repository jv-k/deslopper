"""The deslopper command-line interface."""

import argparse
import json
import os
import sys

from . import __version__
from .config import (
    load_config, DEFAULT_INCLUDE, CONFIG_NAME, RECOMMENDED,
)
from .discovery import resolve_worklist
from .engine import lint_files
from .errors import ConfigError, UsageError
from .evaluate import run_eval
from . import help as help_screen
from . import report, ui

STARTER = {
    "extends": [RECOMMENDED],
    "files": {"include": DEFAULT_INCLUDE, "exclude": []},
}


def _build_parser():
    # add_help=False everywhere: -h/--help are intercepted by help.maybe_help
    # before parsing, so argparse's stock help can never render.
    parser = argparse.ArgumentParser(prog="deslopper", add_help=False)
    parser.add_argument("--version", action="version", version=f"deslopper {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    lint = sub.add_parser("lint", help="lint files and fail on findings", add_help=False)
    lint.add_argument("paths", nargs="*")
    lint.add_argument("--strict", action="store_true")
    lint.add_argument("--config")
    lint.add_argument("--format", choices=["text", "github", "json"], default="text")

    check = sub.add_parser("check", help="report findings, always exit 0", add_help=False)
    check.add_argument("paths", nargs="*")
    check.add_argument("--config")

    rules = sub.add_parser("rules", help="list the active tells", add_help=False)
    rules.add_argument("--config")
    rules.add_argument("--format", choices=["text", "json"], default="text")

    init = sub.add_parser("init", help="write a starter config", add_help=False)
    init.add_argument("--force", action="store_true")

    ev = sub.add_parser("eval", help="judge a rewrite command against the slop fixtures",
                        add_help=False)
    ev.add_argument("rewrite_command", metavar="command",
                    help="shell command under test; {dir} receives the sandbox path")
    ev.add_argument("--keep", action="store_true",
                    help="leave the sandbox on disk and print its path")
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


def _do_lint(args):
    cfg, result = _lint_command(args)
    strict = bool(getattr(args, "strict", False) or cfg.strict)
    pal = ui.palette()
    _emit(result, args.format, pal)
    _finish(result, strict, pal)
    return report.exit_code(result, strict)


def _do_check(args):
    cfg, result = _lint_command(args)
    pal = ui.palette()
    sys.stdout.write(report.format_text(result, pal))
    _finish(result, cfg.strict, pal)
    return 0


def _do_rules(args):
    cfg, _ = load_config(getattr(args, "config", None), os.getcwd())
    if args.format == "json":
        payload = [
            {"name": t.name, "tier": t.tier, "phase": t.phase, "scope": t.scope}
            for t in cfg.tells
        ]
        print(json.dumps(payload, indent=2))
    else:
        pal = ui.palette()
        if pal.enabled:
            # Aligned, tier-coloured columns for eyes; the piped TSV below is
            # the stable machine-side layout.
            name_w = max(len(t.name) for t in cfg.tells)
            for t in cfg.tells:
                tier_style = pal.error if t.tier == "error" else pal.attn
                print(
                    f"  {pal.bold}{t.name:<{name_w}}{pal.reset}  "
                    f"{tier_style}{t.tier:<5}{pal.reset}  "
                    f"{pal.dim}{t.phase:<11} {t.scope:<5}{pal.reset}  {t.message}"
                )
        else:
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
    ui.log_success(ui.palette(), f"wrote {CONFIG_NAME}")
    return 0


def _do_eval(args):
    return run_eval(args.rewrite_command, keep=args.keep)


_COMMANDS = {
    "lint": _do_lint,
    "check": _do_check,
    "rules": _do_rules,
    "init": _do_init,
    "eval": _do_eval,
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
    except (ConfigError, UsageError) as exc:
        ui.log_error(ui.palette(), str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
