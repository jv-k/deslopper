# Agent instructions

deslopper is a deterministic prose linter, Python with the standard library only. When you
work on it, follow these.

## Build and test

    python -m venv .venv && . .venv/bin/activate
    pip install -e . pytest
    pytest -q

Each module has one job: `engine.py` scans lines, `rules.py` compiles kinds, `config.py`
resolves config, `discovery.py` finds files, `report.py` formats, and `cli.py` wires the
commands. Keep them that way. Write a failing test first, then the code.

The lint output is pinned by golden files in `tests/fixtures/`. A change that shifts output
fails the golden test. Update a golden only when the change is intended, and say so in the PR.

## Add a tell or a preset

See [CONTRIBUTING.md](CONTRIBUTING.md). Tells live in
`src/deslopper/presets/recommended.json`. A preset is a `<name>.json` file in
`src/deslopper/presets/`.

## Writing prose (de-slop)

Write docs, comments, commit messages, and PR text plainly, like a sharp engineer. Avoid the
machine-generated tells: em dashes, the section sign, filler verbs, marketing adjectives, the
not-just-X-but-Y pattern, throat-clearing openers, vague intensifiers, reflexive bold labels,
and emoji. Run `deslopper rules` for the full set.

Before finishing any change that touches Markdown, run `deslopper lint` and fix every
error-tier finding. For an intentional example that must contain a tell, wrap it in
`<!-- deslop-lint-disable -->` and `<!-- deslop-lint-enable -->`, or put
`<!-- deslop-lint-disable-line -->` on the offending line.

## Commits

Commit subjects and PR titles follow Conventional Commits (`type(scope): summary`). CI checks
both, on the title and on every commit in a PR.
