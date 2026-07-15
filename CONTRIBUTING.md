# Contributing to deslopper

deslopper is a deterministic prose linter. Most contributions are one of three kinds: a new
tell, a new preset, or a code change. This guide covers all three.

## Development setup

```bash
git clone https://github.com/jv-k/deslopper
cd deslopper
python3 -m venv .venv && . .venv/bin/activate
pip install -e . pytest pre-commit
pre-commit install --hook-type pre-commit --hook-type commit-msg
```

Run the tests with `pytest -q`. Run the linter on the repo's own docs with `deslopper lint`.

## Add a tell to the recommended set

Tells live in `src/deslopper/presets/recommended.json`, one JSON object each. A tell has:

- `name`: a short label, shown in the finding. Names need not be unique across phases.
- `tier`: `error` (fails the run) or `warn` (prints, and fails only under `--strict`).
- `phase`: `pre-entity` (runs before HTML entities are masked) or `post-entity` (the default).
- `kind`: `regex`, `bold-bullet`, or `id-label`. Omit it for `regex`.
- `pattern` or `words`: a regex, or a word list compiled to a boundaried alternation.
- `message`: the text printed after the name.
- `flags`: an optional string of regex flags. Only `i` is supported today.

Add the object, add a case to `tests/fixtures/comprehensive.md`, then regenerate the golden
files: delete `tests/fixtures/comprehensive.*.golden` and run the golden test once. Open a
PR with the tell and the updated goldens.

## Add a preset

A preset is a built-in rule set a project opts into. Drop a `<name>.json` file in
`src/deslopper/presets/` with a top-level `tells` array. A user then references it as
`deslopper:<name>` in the `extends` list of a `deslopper.config.json`. Presets resolve left
to right, and a later tell of the same name and phase replaces an earlier one in place.

Keep a preset to one voice or domain. Say in the PR what it is for and who it serves.

## Code changes

Follow the module layout: one responsibility per file. `engine.py` scans, `rules.py`
compiles kinds, `config.py` resolves, `discovery.py` finds files, `report.py` formats, and
`cli.py` wires the commands. Write a failing test first, make it pass, and keep the suite
green.

## Commits and pull requests

- Commit subjects and the PR title follow [Conventional Commits](https://www.conventionalcommits.org):
  `type(scope): summary`. CI checks the PR title and every commit subject in the PR.
- Lead the PR body with what changed and why. Link the issue it closes.
- The repo lints its own Markdown with deslopper, so keep prose within the rules. Run
  `deslopper lint` before you push.

## Reporting

Open an issue with one of the forms: a bug report for a false positive or a crash, a feature
request for new behaviour, or a tell-or-preset proposal for a new rule.
