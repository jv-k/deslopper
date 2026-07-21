---
name: deslopper
description: Write prose free of the mechanical tells of machine-generated text and verify it with the deslopper linter. Use when writing or editing Markdown or MDX files (docs, READMEs, changelogs), or when the user asks to de-slop text, check for AI tells, or clean up generated prose.
---

# deslopper

deslopper is a deterministic linter for the mechanical tells of machine-generated prose.
This skill has two jobs: write prose that avoids the tells, and prove it with a lint run
before finishing.

## Find the linter and load the rules

Find a runnable deslopper, in this order:

1. `deslopper` on PATH, which respects a project venv or a pinned install
2. `uvx deslopper`, or `pipx run deslopper`

Use the runner you found for every deslopper command in this skill. A command written as
`deslopper rules` here means that runner's spelling, for example `uvx deslopper rules`.

Run `deslopper rules` once when the skill activates. The output is the live tell list for
this project, including its own config and presets. Keep those tells out of every piece of
prose you produce while the skill is active. Write plainly, like a sharp engineer.

If neither command runs, follow the writing guidance anyway, skip the lint steps, and tell
the user in one line that deslopper is not installed. Suggest `pipx install deslopper` or
`brew install jv-k/tap/deslopper`. Never install it yourself.

## Verify before finishing

After writing or editing Markdown or MDX, lint exactly the files you touched, by explicit
path:

    deslopper lint docs/guide.md README.md

Never run a lint without explicit paths, whichever runner you use: a bare lint sweeps
every configured glob in the repo and drags pre-existing findings into your diff.

Handle the findings by tier:

1. Fix every error-tier finding, then re-run until the error tier is clean. For an
   intentional example that must contain a tell, wrap it in `<!-- deslop-lint-disable -->`
   and `<!-- deslop-lint-enable -->`, or put `<!-- deslop-lint-disable-line -->` on the
   offending line.
2. Fix a warn-tier finding only when the rewrite is clearly better. Otherwise leave the
   text as it is and mention the finding to the user.

Findings that predate your edit in a file you touched count as yours: the file is already
in the diff, so fix them by the same tier policy. If that suggests the repo carries a wider
backlog, offer a repo-wide sweep and wait for the user to ask for it.
