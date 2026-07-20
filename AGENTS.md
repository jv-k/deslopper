# Agent instructions

deslopper is a deterministic prose linter, Python with the standard library only. When you
work on it, follow these.

## Build and test

    python3 -m venv .venv && . .venv/bin/activate
    pip install -e . pytest pre-commit
    pre-commit install --hook-type pre-commit --hook-type commit-msg
    pytest -q

Each module has one job. The layout is in [CONTRIBUTING.md](CONTRIBUTING.md) under Code
changes. Keep it that way. Write a failing test first, then the code.

The lint output is pinned by golden files in `tests/fixtures/`. A change that shifts output
fails the golden test. Update a golden only when the change is intended, and say so in the PR.

## Add a tell or a preset

See [CONTRIBUTING.md](CONTRIBUTING.md). Tells live in
`src/deslopper/presets/recommended.json`. A preset is a `<name>.json` file in
`src/deslopper/presets/`.

## Writing prose (de-slop)

Write docs, comments, commit messages, and PR text plainly, like a sharp engineer. Avoid the
machine-generated tells. Run `deslopper rules` for the set.

Before finishing any change that touches Markdown, run `deslopper lint` and fix every
error-tier finding. For an intentional example that must contain a tell, wrap it in
`<!-- deslop-lint-disable -->` and `<!-- deslop-lint-enable -->`, or put
`<!-- deslop-lint-disable-line -->` on the offending line.

## Commits

Commit subjects and PR titles follow Conventional Commits (`type(scope): summary`), checked
by CI. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Agent skills

### Issue tracker

Issues live as GitHub issues in `jv-k/deslopper`, driven by the `gh` CLI.
See [docs/agents/issue-tracker.md](docs/agents/issue-tracker.md).

### Triage labels

The five canonical triage roles, each label string named for its role.
See [docs/agents/triage-labels.md](docs/agents/triage-labels.md).

### Domain docs

Single-context: `CONTEXT.md` and `docs/adr/` at the repo root.
See [docs/agents/domain.md](docs/agents/domain.md).
