# deslopper

A deterministic prose linter for the mechanical tells of machine-generated writing. No
model, no network: it runs in CI and pre-commit and fails the build on a banned tell.

## Install and run

Zero install:

    uvx deslopper lint
    pipx run deslopper lint

Pin a version in CI for reproducible builds:

    uvx deslopper@0.1.0 lint --format github

## Commands

    deslopper lint  [PATHS...] [--strict] [--config P] [--format text|github|json]
    deslopper check [PATHS...] [--config P]   # report only, exits 0 on findings
    deslopper rules [--config P]              # list the active tells
    deslopper init                            # write a starter config

With no paths, deslopper lints the configured Markdown globs, through `git ls-files` in a
work tree or a filesystem walk otherwise.

## Tiers and exit codes

The error tier (em dashes, the section sign) fails the run. The warn tier prints but passes
unless you add `--strict`. Exit codes: 0 clean, 1 a failing-tier finding or an unreadable
file, 2 a usage or configuration error.

## Configure

Drop a `deslopper.config.json` to retune the bundled `recommended` rule set:

    {
      "extends": ["deslopper:recommended"],
      "tells": {
        "disable": ["semicolon"],
        "override": { "filler-verb": { "tier": "error" } },
        "add": [
          { "name": "no-foo", "tier": "warn", "kind": "regex", "pattern": "foo", "message": "no foo" }
        ]
      }
    }

A tell is keyed by its name and phase. Two tells can share a name across phases (the em-dash
entity form and literal form do), so target one with `name@phase`, for example
`em-dash@pre-entity`.

## Disable directives

Exempt an example from the lint with an HTML comment. The directive keyword keeps the
`deslop-lint-` prefix on purpose, so existing documents keep working:

    <!-- deslop-lint-disable-line -->
    <!-- deslop-lint-disable --> ... <!-- deslop-lint-enable -->

## Licence

MIT.
