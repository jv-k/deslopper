# deslopper

<div align="center">
  <img src="https://raw.githubusercontent.com/jv-k/deslopper/main/img/screenshot.png" alt="A bare deslopper run: the rainbow wordmark logo, the version pill, and the USAGE, COMMANDS, OPTIONS, and EXAMPLES sections of the help.">
  <p>
    <a href="https://github.com/jv-k/deslopper/actions/workflows/ci.yml"><img src="https://github.com/jv-k/deslopper/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/licence-MIT-blue.svg" alt="MIT licence"></a>
  </p>
  <p><strong>A slop linter for Markdown.</strong></p>
</div>

Slop is the set of habits that make text read as machine-written: the em-dash aside, the
filler verb, the marketing adjective, the `not just X but Y` padding. deslopper finds slop
in Markdown with plain patterns. It makes no LLM calls. The lint uses no model and no
network, so a run is free, fast, and gives the same result every time. That makes it safe
to use as a gate in CI and pre-commit.

When a pattern is not enough, ask [Jev](https://vercel.com/ai-gateway/models/jev),
TypeSafe AI's System One decision model (`typesafe-ai/jev`) on the Vercel AI Gateway. Jev
brings judgement without the guesswork of an LLM. It does not generate text, so it cannot
invent a rewrite or drift off the question. It answers a fixed question with a typed
verdict and a calibrated probability, in a single pass, and gives consistent answers for
similar inputs. With `--jev`, Jev reads each finding in context and says whether to
rewrite it or keep it. Jev only adds notes, so the gate stays deterministic.

## Highlights

- No LLM calls. A deterministic lint for 20 tells, with an opt-in `aggressive` preset
  for 5 more.
- Jev triage: `deslopper lint --jev` gives each finding a `keep` or `rewrite` verdict
  and a probability, for a fraction of a cent per run.
- An eval for your rewrite pass: `deslopper eval` checks that a model rewrite removes the
  tells and keeps your code, headings, tables, and links. Jev can also score how plainly
  the text reads before and after.
- A skill for coding agents, so the agent writes within the tells and lints its own work.
- No dependencies beyond Python 3.9. It runs in GitHub Actions, pre-commit, and the
  terminal. Install gum as well for colours and spinners on a terminal.

<div align="center">
  <img src="https://raw.githubusercontent.com/jv-k/deslopper/main/img/deslopper-demo.gif" alt="Animated demo: deslopper lint reports an em-dash error and four warnings on a sloppy file, then passes clean after a rewrite.">
</div>

## Contents

- [Getting started](#getting-started)
- [Fix slop with an LLM](#fix-slop-with-an-llm)
  - [With a coding agent](#with-a-coding-agent)
  - [With a script](#with-a-script)
  - [Check the rewrite with `deslopper eval`](#check-the-rewrite-with-deslopper-eval)
- [Why deslopper?](#why-deslopper)
- [Install](#install)
- [Commands](#commands)
- [Tiers and exit codes](#tiers-and-exit-codes)
- [The tells](#the-tells)
- [The `aggressive` preset](#the-aggressive-preset)
- [Configure](#configure)
  - [The fields of a tell](#the-fields-of-a-tell)
- [Disable directives](#disable-directives)
- [Use it in CI](#use-it-in-ci)
- [Use it in pre-commit](#use-it-in-pre-commit)
- [Agent skill](#agent-skill)
- [The `json` format](#the-json-format)
- [Triage findings with Jev](#triage-findings-with-jev)
- [Eval a rewrite pass](#eval-a-rewrite-pass)
- [Contributing](#contributing)
- [Licence](#licence)

## Getting started

1. Install deslopper. On macOS and Linux, Homebrew is the quickest way:

   ```sh
   brew install jv-k/tap/deslopper
   ```

   For pipx, uv, and pip, see [Install](#install).

2. Lint the Markdown in a repo. Run this from the repo root:

   ```sh
   deslopper lint
   ```

   On a terminal with [gum](https://github.com/charmbracelet/gum) installed, deslopper
   gives each file a section. Inside it, each tell appears once with its fix, then every
   place it fired: the line and column, the line itself with the caught words
   highlighted, and a caret under them. The colours show in your terminal:

   ```text
      deslopper  lint                                  1 file, 1 with slop

     notes.md                                          1 error  2 warnings
     ─────────────────────────────────────────────────────────────────────
     ✖ em-dash
       em dash in prose, use a colon, comma, parentheses, or two sentences
         3:20  The fix was simple — restart the server.
                                  ^

     ! filler-verb
       filler verb, use a plain verb or cut
          5:6  This leverages the cache; it is fast.
                    ^

     ! semicolon
       semicolon in prose, prefer a full stop
         5:25  This leverages the cache; it is fast.
                                       ^

     ─────────────────────────────────────────────────────────────────────
     ✖ 1 error   ! 2 warnings
   ```

   On a narrow terminal, the line is cut around the caught words, so nothing wraps.

   Without gum, and whenever the output is piped, deslopper prints one
   `path:line:col [tier] tell: message` line per finding, for editors and scripts.

3. Fix the findings and run the lint again. An error fails the run. A warning only
   reports, unless you add `--strict`. To let an LLM do the fixing, see
   [Fix slop with an LLM](#fix-slop-with-an-llm).

4. Ask Jev which findings to fix. Export your Vercel AI Gateway key, then add `--jev`:

   ```sh
   export AI_GATEWAY_API_KEY=...
   deslopper lint --jev
   ```

   A spinner shows each file while Jev reads it. Each place then starts with Jev's
   rating: a bar, the probability, and the verdict. See
   [Triage findings with Jev](#triage-findings-with-jev).

5. To tune the tells and the files to lint, write a starter config:

   ```sh
   deslopper init
   ```

   See [Configure](#configure) for what the file can do.

6. Add the lint to your pipeline. See [Use it in CI](#use-it-in-ci) and
   [Use it in pre-commit](#use-it-in-pre-commit).

## Fix slop with an LLM

deslopper finds slop, and an LLM can fix it. deslopper never calls an LLM itself, so you
bring your own. The loop is always the same:

1. deslopper lints the files and lists the findings.
2. The LLM rewrites the text at each finding, and changes nothing else.
3. deslopper lints again. The loop ends when no error-tier finding is left.

The lint is the judge in this loop, not the LLM. So the loop ends on a fact, and the LLM
cannot declare the job done too early.

### With a coding agent

[Install the agent skill](#agent-skill), then ask your agent in plain words:

```text
De-slop README.md and docs/.
```

The skill tells the agent to load the active tells, rewrite the text, lint the files it
touched, and repeat until the error tier is clean. It fixes a warning only when the
rewrite is clearly better, and it reports the other warnings to you.

### With a script

Any LLM that can read and edit files works. This example runs Claude Code without a
session, and allows it to run the lint and edit files only:

```sh
claude -p "Run 'deslopper lint --format json docs/'. Fix each finding in place. \
Keep code, headings, tables, and links exactly as they are. \
Run the lint again, and repeat until it exits 0." \
  --allowedTools "Bash(deslopper lint:*)" Read Edit
```

Each finding carries a short fix hint in its `message`, such as "use a plain verb or cut".
The LLM can follow the hint without a long prompt.

On a large backlog, ask Jev first, so that the LLM rewrites only the findings that need
it. This command keeps the findings that Jev did not mark `keep`:

```sh
deslopper lint --jev --format json docs/ | jq '[.findings[] | select(.verdict != "keep")]'
```

### Check the rewrite with `deslopper eval`

An LLM rewrite can remove the tells and still damage the document. `deslopper eval` tests
your rewrite command on sample files before you run it on real ones. It checks that the
tells are gone, and that code, front matter, headings, tables, and links did not change.
Put the rewrite in a script that takes a folder path, then run:

```sh
deslopper eval './scripts/deslop.sh {dir}'
```

See [Eval a rewrite pass](#eval-a-rewrite-pass) for the judges and the exit codes.

## Why deslopper?

An LLM can rewrite machine-written prose, but then each check costs an LLM call and
can give a different answer each run. That does not work as a gate.

deslopper catches the mechanical tells with plain patterns instead. The check costs
nothing, finishes at once, and gives the same findings for the same input. Use deslopper
as the deterministic floor. For the judgement calls that a pattern cannot make, ask Jev.
Jev gives a typed verdict with a probability, not free text. Leave the rewrite itself to
an LLM or to a person.

Vale and proselint check spelling, house style, and readability. deslopper does one
narrower job: it finds the tells of machine-generated writing. It is a single Python
package with no dependencies. If you already run a style linter, add deslopper next to it.

## Install

deslopper needs Python 3.9 or later and has no other dependencies. It is not on PyPI yet.
Install it from the Homebrew tap, or from the GitHub repo with a Python tool.

| Tool | Command |
| --- | --- |
| Homebrew | `brew install jv-k/tap/deslopper` |
| pipx | `pipx install git+https://github.com/jv-k/deslopper` |
| uv | `uv tool install git+https://github.com/jv-k/deslopper` |
| pip | `pip install git+https://github.com/jv-k/deslopper` |

Homebrew also installs the shell completions for bash, zsh, and fish. With pip, install
into a virtual environment, so that deslopper does not change your system Python.

For colours and spinners on a terminal, also install
[gum](https://github.com/charmbracelet/gum) (`brew install gum`). gum is optional.
Without it, deslopper prints plain output and one line that names the install.

To run deslopper once without installing it, use `uvx` or `pipx run`. Each one runs it in
a temporary environment:

    uvx --from git+https://github.com/jv-k/deslopper deslopper lint
    pipx run --spec git+https://github.com/jv-k/deslopper deslopper lint

## Commands

    deslopper lint  [PATHS...] [--strict] [--config P] [--format text|github|json] [--jev]
    deslopper check [PATHS...] [--config P]   # report only, exits 0 on findings
    deslopper rules [--config P]              # list the active tells
    deslopper init                            # write a starter config
    deslopper eval 'COMMAND' [--keep] [--plainness]   # judge a rewrite command
    deslopper completions [bash|zsh|fish]     # print a completion script for your shell

With no paths, deslopper lints the Markdown and MDX files that match the configured globs.
In a git work tree it finds them with `git ls-files`. Outside a work tree it walks the
file system.

A folder path, such as `docs/`, lints the same files that a bare run would lint inside
that folder. A file path lints that file as given, even when the config excludes it.

On a terminal with gum, deslopper draws its output with gum: a header, a section per
file with each tell and the places it fired, a spinner while Jev works, and the totals.
The help screens, the eval report, and the status lines go through gum too.
Piped output, the `github` format, and the `json` format are always plain, and never
call gum. `NO_COLOR`
turns the gum output off. `CLICOLOR_FORCE=1` turns it on without a terminal. These are the
two variables that gum itself reads.

Homebrew installs tab completion for you. For the other install methods, print the script
with `deslopper completions` and save it where your shell reads it. With no argument, the
command uses the shell named in `$SHELL`. Run `deslopper completions --help` to see the
path for each shell.

## Tiers and exit codes

Each tell has a tier:

- An error fails the run. The error tier holds the em dash, the section sign, the
  middle-dot separator, and curly quotes.
- A warn prints the finding but passes the run. Add `--strict` to make warnings fail too.

| Exit code | Meaning |
| --- | --- |
| 0 | No failing finding |
| 1 | A failing finding, or a file deslopper could not read |
| 2 | A usage or configuration error |

## The tells

The `recommended` preset ships these tells. Each row shows a sample of the prose it
catches. The em dash, section sign, middle dot, and curly quotes are also caught when they
are written as HTML entities.

`scripts/readme_tells.py` generates this table from the preset, and the tests check that
each sample fires its tell. To see the tells for your own config, run `deslopper rules`.

<!-- tell-table:begin -->
<!-- deslop-lint-disable -->

❌ error, fails the run. ⚠️ warn, passes unless `--strict`.

| Tell | Tier | Example | Message |
| --- | --- | --- | --- |
| `em-dash` | ❌ | `A quick fix — just restart.` | em dash in prose, use a colon, comma, parentheses, or two sentences |
| `section-sign` | ❌ | `See § 4.2 for details.` | section sign, write 'section' |
| `middle-dot` | ❌ | `fast · simple · tested` | middle dot or bullet in prose, join the items with a comma or plain words, or separate with ◦ |
| `curly-quote` | ❌ | `It’s “done” now.` | curly quote, use a straight quote |
| `bold-bullet-lead` | ⚠️ | `- **Blazing speed** builds finish in seconds` | bolded bullet lead, reserve bold for a rare callout not a per-item label |
| `id-label-lead` | ⚠️ | `- FR-1 The app shall sync.` | id label on a list item, number the list plainly |
| `semicolon` | ⚠️ | `It compiles; it ships.` | semicolon in prose, prefer a full stop |
| `not-just-x-but-y` | ⚠️ | `not just fast but correct` | "not just X but Y" padding, make the point once |
| `filler-verb` | ⚠️ | `This leverages the cache.` | filler verb, use a plain verb or cut |
| `marketing-adjective` | ⚠️ | `a seamless, robust workflow` | marketing adjective, say what is true |
| `throat-clearing` | ⚠️ | `It's worth noting that tests pass.` | throat-clearing or transition opener, start with the point |
| `vague-intensifier` | ⚠️ | `significantly faster` | vague intensifier with no number behind it |
| `emoji` | ⚠️ | `Done ✅` | emoji or decorative checkmark in body text |
| `chatbot-phrase` | ⚠️ | `I hope this helps!` | chatbot phrase, delete it |
| `sycophancy` | ⚠️ | `Great question!` | sycophantic tone, respond directly |
| `fancy-is` | ⚠️ | `The CLI boasts three modes.` | fancy way to say 'is', say 'is' or 'has' |
| `puffery` | ⚠️ | `A testament to good design.` | puffery, state what happened |
| `vague-attribution` | ⚠️ | `Experts believe it scales.` | vague attribution, name the source or cut |
| `inflated-word` | ⚠️ | `A crucial, intricate detail.` | inflated word, use a plain one |
| `trailing-participle` | ⚠️ | `It retries, ensuring delivery.` | trailing participle clause, say it straight or cut |

<!-- deslop-lint-enable -->
<!-- tell-table:end -->

## The `aggressive` preset

The `aggressive` preset adds tells that catch more but also flag more false positives. Use
it when you would rather triage noise than miss a tell. Extend both presets, in this order:

    {
      "extends": ["deslopper:recommended", "deslopper:aggressive"]
    }

No tell in `aggressive` shares a name with a tell in `recommended`, so the preset only adds
tells and replaces none. Some words are also real technical terms, such as vector,
primitive, surface, harness, and scaffolding. The preset leaves those words out, because a
regex cannot tell the metaphor from the term.

<!-- aggressive-table:begin -->
<!-- deslop-lint-disable -->

⚠️ warn throughout: the layer trades precision for reach, and you triage.

| Tell | Tier | Example | Message |
| --- | --- | --- | --- |
| `abstract-metaphor` | ⚠️ | `Our north star is the flywheel.` | abstract metaphor, pick the concrete word |
| `cutoff-disclaimer` | ⚠️ | `Specific details are limited.` | cutoff disclaimer, find the fact or cut |
| `formulaic-challenge` | ⚠️ | `Despite challenges, it continues to thrive.` | formulaic challenge framing, give the specific fact |
| `generic-conclusion` | ⚠️ | `The future looks bright.` | generic conclusion, state a plan or fact |
| `boldface-overuse` | ⚠️ | `**Fast**, **safe**, **simple**.` | three or more bold spans on one line, bold at most one thing |

<!-- deslop-lint-enable -->
<!-- aggressive-table:end -->

## Configure

`deslopper init` writes a `deslopper.config.json`. Edit it to tune the tells and the files
to lint:

    {
      "extends": ["deslopper:recommended"],
      "files": {
        "include": ["**/*.md", "**/*.markdown", "**/*.mdx"],
        "exclude": ["CHANGELOG.md"]
      },
      "tells": {
        "disable": ["semicolon"],
        "override": { "filler-verb": { "tier": "error" } },
        "add": [
          { "name": "no-foo", "tier": "warn", "kind": "regex", "pattern": "foo", "message": "no foo" }
        ]
      }
    }

| Key | What it does |
| --- | --- |
| `extends` | The presets to build on, written as `deslopper:<name>`. `recommended` is the default. |
| `files.include` | The globs to lint when you give no paths. |
| `files.exclude` | The globs to skip when you give no paths. |
| `tells.disable` | The tells to turn off. |
| `tells.override` | Changes to the fields of existing tells. |
| `tells.add` | New tells. |

The [config schema](src/deslopper/schema/config.schema.json) describes the whole file.

### The fields of a tell

| Field | Values | What it does |
| --- | --- | --- |
| `tier` | `error`, `warn` | An `error` fails the run. A `warn` fails only with `--strict`. |
| `phase` | `pre-entity`, `post-entity` | When the tell scans, relative to HTML-entity masking. Only a `pre-entity` tell can catch a tell written as an entity. |
| `scope` | `all`, `first` | `all` reports every match on a line. `first` stops after one. |
| `kind` | `regex`, `bold-bullet`, `id-label` | The matcher. `regex` is the default. The other two kinds read the capture groups of their pattern. |
| `pattern` | a regex | The match, as one regex. |
| `words` | a list of regex fragments | The match, as fragments joined into one alternation with word boundaries. |

A `words` entry is regex, not literal text. For example, `utili[sz]es?` matches
`utilise`, `utilizes`, and the other spellings.

A tell is keyed by its name and its phase. Two tells can share a name in different phases,
as the entity and literal forms of `em-dash` do. To target one of them, write
`name@phase`, for example `em-dash@pre-entity`.

Before the tells scan a file, deslopper masks fenced code, inline code, front matter, and
HTML entities. No tell fires inside them.

## Disable directives

To keep an intentional example, exempt it with an HTML comment. Put this on the line to
skip:

    <!-- deslop-lint-disable-line -->

To skip a block, wrap it:

    <!-- deslop-lint-disable -->
    ...
    <!-- deslop-lint-enable -->

## Use it in CI

This GitHub Actions job fails a pull request that adds an error-tier tell. The job installs
deslopper from the GitHub repo, because it is not on PyPI yet. To keep the gate stable,
replace `main` with a release tag, such as `v1.4.0`.

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

The `github` format writes each finding as an annotation on the pull request.

If the repo has prose from before you added deslopper, lint only the files that the pull
request changes. Then the old findings do not block every change:

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

## Use it in pre-commit

To run the same lint before each commit, add a local hook to
[pre-commit](https://pre-commit.com):

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

The hook runs the deslopper on your `PATH`, so [install it](#install) first.

`pass_filenames: false` makes the hook lint the configured globs, not the staged files.
This keeps the local result the same as the CI result. deslopper lints explicit file
paths as given and ignores the config excludes for them. So a hook that passes the staged
files would flag files that your config excludes.

## Agent skill

The repo ships a skill in [skills/deslopper/](skills/deslopper/). The skill is for coding
agents that follow the skills convention, such as Claude Code.

Install it with the skills CLI:

    npx skills add jv-k/deslopper

You can also copy `skills/deslopper/` by hand. Put it in `~/.claude/skills/` to use it in
every project. Put it in a repo's `.claude/skills/` to use it in that repo only.

The skill activates when the agent writes or edits Markdown or MDX. It also activates when
you ask the agent to de-slop existing text. The agent then does these steps:

1. It runs `deslopper rules` to load the active tells. The list follows your config and
   presets.
2. It writes within those tells.
3. Before it finishes, it lints the files it touched.
4. It fixes every error-tier finding and lints again, until no error-tier finding is left.
5. It fixes a warn-tier finding only when the rewrite is clearly better. It reports the
   other warn-tier findings to you.

The skill is the model-side complement to the CI gate. The gate stays the deterministic
floor.

## The `json` format

`deslopper lint --format json` is the format for tools and for models. It prints one JSON
object to stdout and nothing to stderr, so the payload is the whole output. Only a usage
error, such as a missing gateway key, prints one line to stderr and exits 2.

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

With `--jev`, the object also has a `jev` key with the totals of the run. Its `errors`
list has one line for each Jev request that failed:

    "jev": { "keep": 2, "rewrite": 1, "tokens": 872, "cost": "0.000032844", "errors": [] }

The package ships a JSON Schema for each side of the contract:
[output.schema.json](src/deslopper/schema/output.schema.json) for this object, and
[config.schema.json](src/deslopper/schema/config.schema.json) for the config file.

## Triage findings with Jev

A regex cannot tell a decorative em dash from one inside a quoted title. It also cannot
tell `delve` the filler verb from Delve the debugger. So on a repo with real prose, the
warn tier fills up with findings that a careful editor would keep.

`deslopper lint --jev` runs the normal scan first. Then it sends each flagged line,
with the line above and below it, to [Jev](https://vercel.com/ai-gateway/models/jev)
(`typesafe-ai/jev`) through the
[Vercel AI Gateway](https://vercel.com/docs/ai-gateway). For each finding it asks one
question: is this a machine-writing habit to rewrite, or a deliberate use to keep? Each
finding comes back with a verdict and a probability. On a terminal with gum, a spinner
names each file while Jev reads it, and each place then starts with Jev's rating:

```text
  ✖ em-dash
    em dash in prose, use a colon, comma, parentheses, or two sentences
      ❚❚❚❚❚ 0.76 keep     3:20  The fix was simple — restart the server.
                                                   ^

  ! filler-verb
    filler verb, use a plain verb or cut
      ❚❚❚❚❚ 0.87 rewrite   5:6  This leverages the cache; it is fast.
                                     ^

  ──────────────────────────────────────────────────────────────────────────────────
  ✖ 1 error   ! 2 warnings
  Jev 1 rewrite  ·  2 keep  ·  872 tokens  ·  $0.000032844
```

The bar fills in proportion to the probability. Its filled slots are green from 0.9,
yellow from 0.7, and red below that. On a narrow terminal the rating drops the number
and keeps the bar and the verdict.

Piped output adds the verdict to the end of each line, such as `[rewrite 0.87]`. The
`json` format adds `verdict` and `probability` to each judged finding. The `github`
format puts the verdict in the annotation message. The plain summary line counts the
`keep` and `rewrite` verdicts, and reports the tokens and the gateway cost of the run.

Triage only adds notes. It never changes the exit code, so a `keep` verdict cannot make a
lint pass, and the deterministic gate holds in CI. Some other limits apply:

- deslopper never sends findings on a disabled line.
- A file with no findings sends no request. A file with findings sends one request.
- `--jev` is a command-line flag only, never a config key. So no repo can turn on
  network calls for everyone who lints it.
- `check` does not accept `--jev`.
- `--triage`, the old name of the flag, still works.

The gateway key comes from `AI_GATEWAY_API_KEY`. Without it, `--jev` exits 2 with a
one-line hint and prints no findings. A test run of nine findings cost $0.000066 and took
less than half a second. If a request fails, deslopper prints one error line to stderr,
leaves the findings of that file without verdicts, and exits with the code of the scan.
With `--format json`, the error goes into the payload instead.

## Eval a rewrite pass

The linter is the deterministic floor. To clear a backlog, you need a rewrite, which is a
model pass. `deslopper eval` tests whether your rewrite works:

1. It puts sample files that trip every tell in the `recommended` and `aggressive` presets
   into a temporary folder.
2. It runs your rewrite command over the folder.
3. It judges the result.

Give the command with `{dir}` where the folder path goes. If you leave out `{dir}`,
deslopper adds the path at the end:

    deslopper eval 'my-rewrite {dir}'
    deslopper eval ./scripts/deslop.sh

Two judges decide the result:

- Efficacy lints the rewritten files. It needs zero error-tier findings. The warn count
  must also fall below the count before the rewrite. This gives the model some room, but it
  cannot leave the warnings as they were.
- Preservation compares the protected content before and after the rewrite. That is
  fenced code and front matter, exactly, plus the heading outline, the table rows, and the
  link targets. Any difference fails the run.

Before the rewrite, deslopper also lints the raw sample files as a self-check. If they give
no errors, the harness is broken, and the run stops before it spends tokens.

| Exit code | Meaning |
| --- | --- |
| 0 | Pass |
| 1 | Efficacy failure |
| 2 | A usage or configuration error |
| 3 | Preservation failure |
| 4 | A broken harness, or a rewrite command that exited nonzero |

A failure names the remaining findings by file and line. To keep the temporary folder for
inspection, add `--keep`.

`--plainness` adds a third judge. It asks Jev to score how plainly each sample file reads.
It scores the files once before the rewrite and once after, and prints one
`before -> after` line per file plus the mean.
The score is only a report. It never changes the verdict or the exit code. So you can
compare two eval runs on more than pass or fail, and a probabilistic judge cannot fail a
run that the deterministic judges passed.

`--plainness` needs `AI_GATEWAY_API_KEY`. Without it, the eval exits 2 before the rewrite
command runs. The two requests send the sample files whole. A run costs about a thousand
input tokens and a fraction of a cent, and the mean line reports the cost. If the gateway
fails, deslopper prints one error line and finishes with the two deterministic judges.

An eval runs your rewrite command for real, so it spends real minutes and tokens. Run it
when you change the rewrite prompt or model. Do not run it as a gate on each commit or pull
request.

## Contributing

You can add a tell, add a preset, or change the code. See
[CONTRIBUTING.md](CONTRIBUTING.md). The tells live in
`src/deslopper/presets/recommended.json`. A preset is a `<name>.json` file in
`src/deslopper/presets/`, and a config opts into it as `deslopper:<name>`.

## Licence

MIT.
