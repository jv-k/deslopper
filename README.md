# deslopper

<div align="center">
  <img src="https://raw.githubusercontent.com/jv-k/deslopper/main/img/screenshot.png" alt="A bare deslopper run: the rainbow wordmark logo, the version pill, and the USAGE, COMMANDS, OPTIONS, and EXAMPLES sections of the help.">
  <p>
    <a href="https://github.com/jv-k/deslopper/actions/workflows/ci.yml"><img src="https://github.com/jv-k/deslopper/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/licence-MIT-blue.svg" alt="MIT licence"></a>
  </p>
</div>

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

Vale and proselint lint prose style at large, covering spelling, house style, and
readability. deslopper is narrower on purpose. It targets the tells of machine-generated
writing, ships as one Python package with no dependencies, and gives the same answer on
every run. If you already run a style linter, deslopper sits beside it as the
machine-prose gate.

## Install and run

deslopper needs no runtime dependencies beyond Python 3.9+. It is published to PyPI and to a
Homebrew tap on each tagged release.

Run it straight from PyPI with uv:

    uvx deslopper lint

or with pipx:

    pipx run deslopper lint

Install it with pipx:

    pipx install deslopper

with plain pip:

    pip install deslopper

or from the Homebrew tap:

    brew install jv-k/tap/deslopper

Pin a version in CI for reproducible builds:

    uvx deslopper@0.2.0 lint --format github

## Demo

<div align="center">
  <img src="https://raw.githubusercontent.com/jv-k/deslopper/main/img/deslopper-demo.gif" alt="Animated demo: deslopper lint reports an em-dash error and four warnings on a sloppy file, then passes clean after a rewrite.">
</div>

## Commands

    deslopper lint  [PATHS...] [--strict] [--config P] [--format text|github|json]
    deslopper check [PATHS...] [--config P]   # report only, exits 0 on findings
    deslopper rules [--config P]              # list the active tells
    deslopper init                            # write a starter config
    deslopper eval 'COMMAND' [--keep]         # judge a rewrite command, see below
    deslopper completions [bash|zsh|fish]     # print a completion script for your shell

With no paths, deslopper lints the configured Markdown and MDX globs, through `git ls-files`
in a work tree or a filesystem walk otherwise.

Tab completion comes from `deslopper completions`, which detects your shell from `$SHELL`
when you leave the argument off. Run `deslopper completions --help` for where each shell
expects the script.

Output is coloured on a terminal and plain when piped. `NO_COLOR` turns styling off
everywhere, `FORCE_COLOR=1` turns it on without a terminal, and the `github` and `json`
formats are never styled.

## Tiers and exit codes

The error tier (em dashes, the section sign, middle-dot separators) fails the run. The warn
tier prints but passes unless you add `--strict`. Exit codes: 0 clean, 1 a failing-tier
finding or an unreadable file, 2 a usage or configuration error.

## The tells

The `recommended` preset ships these. A name appears twice when the tell scans in both
phases, before and after HTML entities are masked, and only the pre-entity form catches
the tic spelled as an entity. The table is generated from the preset by
`scripts/readme_tells.py` and pinned by a test, and `deslopper rules` prints the live
list for whatever config is active.

<!-- tell-table:begin -->
<!-- deslop-lint-disable -->

| Tell | Tier | Phase | Message |
| --- | --- | --- | --- |
| `em-dash` | error | pre-entity | em dash as an HTML entity, write it out plainly |
| `section-sign` | error | pre-entity | section sign as an HTML entity, write 'section' |
| `middle-dot` | error | pre-entity | middle dot or bullet as an HTML entity, join the items with a comma or plain words |
| `em-dash` | error | post-entity | em dash in prose, use a colon, comma, parentheses, or two sentences |
| `section-sign` | error | post-entity | section sign, write 'section' |
| `middle-dot` | error | post-entity | middle dot or bullet in prose, join the items with a comma or plain words |
| `bold-bullet-lead` | warn | post-entity | bolded bullet lead, reserve bold for a rare callout not a per-item label |
| `id-label-lead` | warn | post-entity | id label on a list item, number the list plainly |
| `semicolon` | warn | post-entity | semicolon in prose, prefer a full stop |
| `not-just-x-but-y` | warn | post-entity | "not just X but Y" padding, make the point once |
| `filler-verb` | warn | post-entity | filler verb, use a plain verb or cut |
| `marketing-adjective` | warn | post-entity | marketing adjective, say what is true |
| `throat-clearing` | warn | post-entity | throat-clearing or transition opener, start with the point |
| `vague-intensifier` | warn | post-entity | vague intensifier with no number behind it |
| `emoji` | warn | post-entity | emoji or decorative checkmark in body text |

<!-- deslop-lint-enable -->
<!-- tell-table:end -->

## The `json` format

`deslopper lint --format json` prints one object for tooling:

    {
      "findings": [
        {
          "path": "docs/guide.md",
          "line": 6,
          "col": 27,
          "tier": "warn",
          "name": "semicolon",
          "message": "semicolon in prose, prefer a full stop"
        }
      ],
      "unreadable": [],
      "summary": { "errors": 0, "warnings": 1, "unreadable": 0 }
    }

The package ships JSON Schemas for both sides of the contract:
[output.schema.json](src/deslopper/schema/output.schema.json) for this object and
[config.schema.json](src/deslopper/schema/config.schema.json) for the config file.

## Eval a rewrite pass

The linter is the deterministic floor. The rewrite that clears a backlog is a model pass,
and `deslopper eval` tests whether yours works: it seeds a temporary sandbox with slop
fixtures that trip every tell in the recommended preset, runs your rewrite command over the
sandbox, and judges the result.

    deslopper eval 'my-rewrite {dir}'
    deslopper eval ./scripts/deslop.sh    # the sandbox path is appended when {dir} is absent

Two judges rule on the outcome. Efficacy lints the rewritten fixtures: zero error-tier
findings is the hard gate, and the warn count must land strictly below the raw baseline,
which leaves the model some room without letting it tread water. Preservation extracts a
digest of the protected content (fenced code and front matter verbatim, the heading
outline, table rows, link destinations) before and after the rewrite, and any difference
fails the run. As a self-check, the raw fixtures are linted first: if they produce no
errors the harness is broken and the run aborts before spending tokens.

Exit codes: 0 pass, 1 efficacy failure, 2 usage or configuration error, 3 preservation
failure, 4 broken harness or a rewrite command that exited nonzero. A failure names the
surviving findings by file and line. Pass `--keep` to keep the sandbox for inspection.

An eval run invokes your rewrite command for real, with the minutes and tokens that
implies. Run it on demand when you change the rewrite prompt or model. It has no place as
a per-commit or per-PR gate.

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

For a local gate, run the same lint from [pre-commit](https://pre-commit.com):

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: deslopper
        name: deslopper
        entry: deslopper lint
        language: system
        types: [markdown]
        pass_filenames: false
```

The hook shells out to whichever deslopper is on your path, so install it first through
pipx or Homebrew. `pass_filenames: false` makes the hook lint the configured globs rather
than the staged paths, which keeps the local verdict identical to CI. Explicit paths are
linted as given, skipping the config excludes, so a staged-files hook would flag files
your config meant to leave alone.

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

A tell has a `tier`, either `error` or `warn` and nothing else. Its `phase`, `pre-entity`
or `post-entity`, says when it scans relative to HTML-entity masking, and only a
pre-entity tell can catch a tic spelled as an entity. A `scope` of `all` reports every
match on a line, `first` stops after one. The `kind` picks the matcher: `regex` is the
default, and the `bold-bullet` and `id-label` kinds read their pattern's capture groups.
The match itself is either `pattern`, one regex, or `words`, a list of regex fragments
joined into a single boundaried alternation, so an entry like `utili[sz]es?` is a fragment
and not a literal string.

Fenced code, inline code, front matter, and HTML entities are masked before tells scan, so
no tell fires inside them.

`extends` names the presets to build on, opted into as `deslopper:<name>`. `recommended`
is the only preset shipped today. The whole file is described by the
[config schema](src/deslopper/schema/config.schema.json).

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
