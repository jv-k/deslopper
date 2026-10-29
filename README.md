# deslopper

<div align="center">
  <img src="https://raw.githubusercontent.com/jv-k/deslopper/main/img/deslopper-demo.gif" alt="Animated demo: deslopper lint shows an em-dash error and four warnings, each tell with its fix and a caret under the caught words. A lint --jev run then rates each place with a bar, a probability and a rewrite verdict, and after a rewrite the file lints clean.">
  <p>
    <a href="https://github.com/jv-k/deslopper/actions/workflows/ci.yml"><img src="https://github.com/jv-k/deslopper/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
    <a href="https://github.com/jv-k/deslopper/releases/latest"><img src="https://img.shields.io/github/v/release/jv-k/deslopper" alt="Latest release"></a>
    <img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python 3.10 or later">
    <a href="LICENSE"><img src="https://img.shields.io/badge/licence-MIT-blue.svg" alt="MIT licence"></a>
  </p>
  <p><strong>A slop linter for Markdown.</strong></p>
</div>

Slop is the set of habits that make text read as machine-written: the em-dash aside, the
filler verb, the marketing adjective, the `not just X but Y` padding. deslopper finds slop
in Markdown with plain patterns. It uses no model and no network, so a run is free, fast,
and gives the same findings for the same input. That makes it safe to use as a gate in CI
and pre-commit, where an LLM check would cost a call each run and could change its answer.

deslopper does one narrow job. It does not check spelling, grammar, house style, or
readability. Tools such as [Vale](https://vale.sh) and proselint do that, and deslopper
runs next to them.

For the judgement calls that a pattern cannot make, `--jev` asks the
[Jev](docs/jev.md) decision model whether to keep or rewrite each finding. Jev only adds
notes. It never changes the result of the lint.

## Highlights

- A deterministic lint for 30 tells, with an opt-in `aggressive` preset for 7 more.
- Jev triage: `deslopper lint --jev` gives each finding a `keep` or `rewrite` verdict and
  a probability. A file with findings costs one request, at a fraction of a cent, and a
  disk cache skips the findings that did not change.
- An eval for your rewrite pass: `deslopper eval` checks that a model rewrite removes the
  tells and keeps your code, headings, tables, and links.
- A skill for coding agents, so the agent writes within the tells and lints its own work.
- No dependencies beyond Python 3.10. It runs in GitHub Actions, pre-commit, and the
  terminal.

## Contents

- [Getting started](#getting-started)
- [The tells](#the-tells)
- [Install](#install)
- [Use it in CI](#use-it-in-ci)
- [Use it in pre-commit](#use-it-in-pre-commit)
- [Configure](#configure)
- [Fix slop with an LLM](#fix-slop-with-an-llm)
- [Agent skill](#agent-skill)
- [Triage findings with Jev](#triage-findings-with-jev)
- [Commands](#commands)
- [Contributing](#contributing)

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

   deslopper gives each file a section. Inside it, each tell appears once with its fix,
   then every place it fired, with a caret under the caught words:

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

   This view needs [gum](https://github.com/charmbracelet/gum), a tool from Charm that
   draws styled output in a terminal. Without gum, and whenever the output is piped,
   deslopper prints one `path:line:col [tier] tell: message` line per finding. See
   [Output formats](docs/output.md).

3. Fix the findings and run the lint again. An error fails the run. A warning only
   reports, unless you add `--strict`. To let an LLM do the fixing, see
   [Fix slop with an LLM](#fix-slop-with-an-llm).

4. To tune the tells and the files to lint, write a starter config with
   `deslopper init`. See [Configure](#configure).

5. Add the lint to your pipeline. See [Use it in CI](#use-it-in-ci) and
   [Use it in pre-commit](#use-it-in-pre-commit).

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
| `false-exclusivity` | ⚠️ | `Nobody talks about the cost.` | claim that others miss the point, make the point and cite who missed it |
| `hidden-truth` | ⚠️ | `The uncomfortable truth: tests rot.` | promised hidden truth, state the fact plainly |
| `real-problem-reframe` | ⚠️ | `The real problem isn't speed.` | reframe to a "real" problem, name the problem and show why |
| `false-suspense` | ⚠️ | `Here's the thing: it caches.` | false suspense before a reveal, start with the point |
| `rhetorical-self-answer` | ⚠️ | `The catch? It only runs on Linux.` | question answered at once, state the answer as a sentence |
| `emphasis-crutch` | ⚠️ | `It never drops a job. Let that sink in.` | emphasis crutch, cut it and let the point stand |
| `staged-candor` | ⚠️ | `Honestly? It depends.` | staged candor, drop the honesty marker and make the claim |
| `mic-drop` | ⚠️ | `That's the whole point.` | mic-drop line that grades the point, cut it or add a fact |
| `negation-pivot` | ⚠️ | `It's not a bug. It's a feature.` | "it's not X, it's Y" pivot, say what it is |
| `importance-flag` | ⚠️ | `This matters because retries add up.` | says it matters instead of showing why, give the consequence |
| `signposting` | ⚠️ | `In conclusion, the cache works.` | essay signpost, cut the announcement and keep the point |
| `urgency-inflation` | ⚠️ | `Fast builds have never been more critical.` | inflated stakes, give the reason it is urgent |
| `stacked-hedge` | ⚠️ | `The job could potentially fail.` | stacked hedge, keep one hedge or none |
| `tradeoff-dodge` | ⚠️ | `Fast without sacrificing safety.` | claims the gain costs nothing, state the tradeoff or show there is none |

<!-- deslop-lint-enable -->
<!-- tell-table:end -->

### Tiers and exit codes

An error fails the run. A warn prints the finding but passes the run. Add `--strict` to
make warnings fail too.

| Exit code | Meaning |
| --- | --- |
| 0 | No failing finding |
| 1 | A failing finding, or a file deslopper could not read |
| 2 | A usage or configuration error |

### The `aggressive` preset

The `aggressive` preset adds tells that catch more but also flag more false positives. Use
it when you would rather triage noise than miss a tell. Extend both presets, in this order:

```json
{
  "extends": ["deslopper:recommended", "deslopper:aggressive"]
}
```

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
| `strong-intensifier` | ⚠️ | `It is genuinely fast.` | strong intensifier, cut it or give the evidence |
| `unicode-arrow` | ⚠️ | `Build → test → ship.` | arrow in prose, write the step or the cause in words |

<!-- deslop-lint-enable -->
<!-- aggressive-table:end -->

## Install

deslopper needs Python 3.10 or later and has no other dependencies. It is not on PyPI yet.
Install it from the Homebrew tap, or from the GitHub repo with a Python tool.

| Tool | Command |
| --- | --- |
| Homebrew | `brew install jv-k/tap/deslopper` |
| pipx | `pipx install git+https://github.com/jv-k/deslopper` |
| uv | `uv tool install git+https://github.com/jv-k/deslopper` |
| pip | `pip install git+https://github.com/jv-k/deslopper` |

With pip, install into a virtual environment, so that deslopper does not change your
system Python.

For colours and spinners on a terminal, also install
[gum](https://github.com/charmbracelet/gum) (`brew install gum`). gum is optional. Without
it, deslopper prints plain output and one line that names the install.

Homebrew also installs the shell completions for bash, zsh, and fish. For the other
install methods, print the script with `deslopper completions` and save it where your
shell reads it. Run `deslopper completions --help` to see the path for each shell.

To run deslopper once without installing it, use `uvx` or `pipx run`. Each one runs it in
a temporary environment:

```sh
uvx --from git+https://github.com/jv-k/deslopper deslopper lint
pipx run --spec git+https://github.com/jv-k/deslopper deslopper lint
```

To update, run `deslopper update`. It runs the upgrade of the tool that installed
deslopper. Read the [changelog](CHANGELOG.md) first, because a new release can add a tell
or change a tier. See [Update deslopper](docs/update.md) for the other setups.

## Use it in CI

This GitHub Actions job fails a pull request that adds an error-tier tell. The job installs
deslopper from a release tag of the GitHub repo, because it is not on PyPI yet. Pin the
[latest release](https://github.com/jv-k/deslopper/releases/latest), so that a new tell
does not fail your build without warning.

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
      - run: uvx --from git+https://github.com/jv-k/deslopper@v1.7.2 deslopper lint --format github
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
    uvx --from git+https://github.com/jv-k/deslopper@v1.7.2 deslopper lint --format github $files
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

## Configure

`deslopper init` writes a `deslopper.config.json`. In it, you can choose the presets, the
files to lint, and turn tells off, change them, or add your own:

```json
{
  "extends": ["deslopper:recommended"],
  "files": { "exclude": ["CHANGELOG.md"] },
  "tells": {
    "disable": ["semicolon"],
    "override": { "filler-verb": { "tier": "error" } }
  }
}
```

To keep an intentional example, exempt it with an HTML comment. Put
`<!-- deslop-lint-disable-line -->` on the line, or wrap a block in
`<!-- deslop-lint-disable -->` and `<!-- deslop-lint-enable -->`. No tell fires inside
fenced code, inline code, or front matter.

See [Configure deslopper](docs/configure.md) for every key and the fields of a tell.

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
The LLM can follow the hint without a long prompt. On a large backlog,
[ask Jev first](docs/jev.md#send-only-the-findings-that-need-a-rewrite), so that the LLM
rewrites only the findings that need it.

### Check the rewrite with `deslopper eval`

An LLM rewrite can remove the tells and still damage the document. `deslopper eval` tests
your rewrite command on sample files before you run it on real ones. It checks that the
tells are gone, and that code, front matter, headings, tables, and links did not change.
Put the rewrite in a script that takes a folder path, then run:

```sh
deslopper eval './scripts/deslop.sh {dir}'
```

See [Eval a rewrite pass](docs/eval.md) for the judges and the exit codes.

## Agent skill

The repo ships a skill in [skills/deslopper/](skills/deslopper/). The skill is for coding
agents that follow the skills convention, such as Claude Code.

Install it with the skills CLI:

```sh
npx skills add jv-k/deslopper
```

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

## Triage findings with Jev

A regex cannot tell a decorative em dash from one inside a quoted title. So on a repo with
real prose, the warn tier fills up with findings that a careful editor would keep.

`deslopper lint --jev` sends each finding, with the lines around it, to
[Jev](https://vercel.com/ai-gateway/models/jev) (`typesafe-ai/jev`) through the
[Vercel AI Gateway](https://vercel.com/docs/ai-gateway). Jev is a decision model, not a
text generator. It answers one question for each finding: rewrite it, or keep it? Each
finding comes back with a verdict and a probability:

```sh
export AI_GATEWAY_API_KEY=...
deslopper lint --jev
```

```text
  ✖ em-dash
    em dash in prose, use a colon, comma, parentheses, or two sentences
      ❚❚❚❚❚ 0.76 keep     3:20  The fix was simple — restart the server.
                                                   ^
```

Triage never changes the exit code, so a `keep` verdict cannot make a lint pass. A disk
cache keeps each verdict, so a later run asks Jev only about new or changed findings.
`--jev` is a command-line flag only, so no repo can turn on network calls for everyone who
lints it.

See [Triage findings with Jev](docs/jev.md) for the output, the cache, and the limits.

## Commands

```text
deslopper lint  [PATHS...] [--strict] [--config P] [--format text|github|json] [--jev] [--no-cache]
deslopper check [PATHS...] [--config P]   # report only, exits 0 on findings
deslopper rules [--config P]              # list the active tells
deslopper init                            # write a starter config
deslopper eval 'COMMAND' [--keep] [--plainness]   # judge a rewrite command
deslopper completions [bash|zsh|fish]     # print a completion script for your shell
deslopper update [--dry-run]              # update with the tool that installed it
```

With no paths, deslopper lints the Markdown and MDX files that match the configured globs.
A file path lints that file as given, even when the config excludes it. For the formats,
see [Output formats](docs/output.md).

<div align="center">
  <img src="https://raw.githubusercontent.com/jv-k/deslopper/main/img/screenshot.png" alt="A bare deslopper run: the rainbow wordmark logo, the version pill, and the USAGE, COMMANDS, OPTIONS, and EXAMPLES sections of the help.">
</div>

## Contributing

You can add a tell, add a preset, or change the code. See
[CONTRIBUTING.md](CONTRIBUTING.md). The tells live in
`src/deslopper/presets/recommended.json`. A preset is a `<name>.json` file in
`src/deslopper/presets/`, and a config opts into it as `deslopper:<name>`.

## Licence

MIT.
