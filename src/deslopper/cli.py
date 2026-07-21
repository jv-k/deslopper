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
from . import report

STARTER = {
    "extends": [RECOMMENDED],
    "files": {"include": DEFAULT_INCLUDE, "exclude": []},
}


def _build_parser():
    parser = argparse.ArgumentParser(prog="deslopper")
    parser.add_argument("--version", action="version", version=f"deslopper {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    lint = sub.add_parser("lint", help="lint files and fail on findings")
    lint.add_argument("paths", nargs="*")
    lint.add_argument("--strict", action="store_true")
    lint.add_argument("--config")
    lint.add_argument("--format", choices=["text", "github", "json"], default="text")

    check = sub.add_parser("check", help="report findings, always exit 0")
    check.add_argument("paths", nargs="*")
    check.add_argument("--config")

    rules = sub.add_parser("rules", help="list the active tells")
    rules.add_argument("--config")
    rules.add_argument("--format", choices=["text", "json"], default="text")

    init = sub.add_parser("init", help="write a starter config")
    init.add_argument("--force", action="store_true")

    ev = sub.add_parser("eval", help="judge a rewrite command against the slop fixtures")
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


def _emit(result, fmt):
    if fmt == "text":
        sys.stdout.write(report.format_text(result))
    elif fmt == "github":
        sys.stdout.write(report.format_github(result))
    elif fmt == "json":
        sys.stdout.write(report.format_json(result))


def _do_lint(args):
    cfg, result = _lint_command(args)
    strict = bool(getattr(args, "strict", False) or cfg.strict)
    _emit(result, args.format)
    for path in result.unreadable:
        print(f"deslopper: cannot read {path}", file=sys.stderr)
    print(report.summary_line(result, strict), file=sys.stderr)
    return report.exit_code(result, strict)


def _do_check(args):
    cfg, result = _lint_command(args)
    sys.stdout.write(report.format_text(result))
    for path in result.unreadable:
        print(f"deslopper: cannot read {path}", file=sys.stderr)
    print(report.summary_line(result, cfg.strict), file=sys.stderr)
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
    print(f"wrote {CONFIG_NAME}")
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
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return _COMMANDS[args.command](args)
    except (ConfigError, UsageError) as exc:
        print(f"deslopper: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
