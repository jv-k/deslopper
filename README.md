# deslopper

A deterministic prose linter for the mechanical tells of machine-generated writing. No
model, no network: it runs in CI and pre-commit and fails the build on a banned tell.

## Why?

Machine-generated prose has tells: the em-dash aside, the filler verb, the marketing
adjective, the `not just X but Y` padding, the throat-clearing opener, the `G1`/`NG2` label
stapled to every item of a list. A model can rewrite them away, but that costs a model call
on every check and gives a different result each run.
deslopper catches the mechanical tells with plain patterns, so the check is free, instant,
and identical every time. That makes it safe as a gate in CI and pre-commit, where a model
pass does not belong. Use it for the deterministic floor, and leave the model rewrite for
the judgement a regex cannot make.

## Install and run

deslopper needs no runtime dependencies beyond Python 3.9+. It is published to PyPI and to a
Homebrew tap on each tagged release.

From PyPI, with no install:

    uvx deslopper lint
    pipx run deslopper lint

Or install it:

    pipx install deslopper
    pip install deslopper

From Homebrew:

    brew install jv-k/tap/deslopper

Pin a version in CI for reproducible builds:

    uvx deslopper@0.1.0 lint --format github

## Commands

    deslopper lint  [PATHS...] [--strict] [--config P] [--format text|github|json]
    deslopper check [PATHS...] [--config P]   # report only, exits 0 on findings
    deslopper rules [--config P]              # list the active tells
    deslopper init                            # write a starter config

With no paths, deslopper lints the configured Markdown and MDX globs, through `git ls-files`
in a work tree or a filesystem walk otherwise.

## Tiers and exit codes

The error tier (em dashes, the section sign, middle-dot separators) fails the run. The warn
tier prints but passes unless you add `--strict`. Exit codes: 0 clean, 1 a failing-tier
finding or an unreadable file, 2 a usage or configuration error.

## Use it in CI

Run deslopper as a gate with GitHub Actions. Until it is on PyPI, install it from the public
repo. Switch to the pinned PyPI form (`uvx deslopper@x.y.z ...`) once it ships.

```yaml
# .github/workflows/prose.yml
name: Prose
on: pull_request
permissions:
  contents: read
jobs:
  deslop:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v8.2.0
      - run: uvx --from git+https://github.com/jv-k/deslopper@main deslopper lint --format github
```

On a repo whose prose predates the rules, lint only the files changed in the PR, so the
backlog does not block every commit:

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
- uses: astral-sh/setup-uv@v8.2.0
- run: |
    files=$(git diff --name-only "origin/${{ github.base_ref }}...HEAD" -- '*.md' '*.markdown' '*.mdx')
    [ -z "$files" ] && exit 0
    uvx --from git+https://github.com/jv-k/deslopper@main deslopper lint --format github $files
```

For a local gate, add a pre-commit hook that runs the same command on staged Markdown.

## Use it as an agent skill

The repo ships a skill in [skills/deslopper/](skills/deslopper/) that teaches a coding
agent to write within the rules and to lint the Markdown it touches before finishing. The
skill runs `deslopper rules` to pick up the live tell list, so it follows your config and
presets. Install it with the skills CLI:

    npx skills add jv-k/deslopper

Or copy `skills/deslopper/` into `~/.claude/skills/` for every project, or into a repo's
`.claude/skills/` for that repo alone. The skill is the model-side complement to the CI
gate, and the gate stays the deterministic floor.

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

## Contributing

Add a tell, add a preset, or change the code. See [CONTRIBUTING.md](CONTRIBUTING.md). Tells
live in `src/deslopper/presets/recommended.json`. A preset is a `<name>.json` file in
`src/deslopper/presets/`, opted into from a config as `deslopper:<name>`.

## Licence

MIT.
