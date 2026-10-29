## What to build

Bring the code, the output, and the docs in line with the glossary in `CONTEXT.md`. The
glossary now uses these terms:

- Smell: one place where a tell matched. It replaces "finding", which is now a word
  to avoid. A smell has the tier of its tell, so there are error smells and warn smells.
- Exempt region and exempt line: the lines that a `deslop-lint-disable` or
  `deslop-lint-disable-line` comment takes out of the scan.
- Disable: removing a tell from the project's set in the config. It no longer names
  the effect of the comment.
- Skipped line, masking, active tells, and tell identity
  (`name@phase`) are also defined in `CONTEXT.md`.

This is a rename only. Do not change behaviour.

## Decisions already made

- The json output key `"findings"` becomes `"smells"`. This breaks scripts and models that
  read the json payload, so the change ships as a major release (2.0.0) with a migration
  note in `CHANGELOG.md`. Make the commit a breaking change (`feat!:` or a
  `BREAKING CHANGE:` footer).
- Do not change the text of the Jev prompt in `src/deslopper/triage.py` (`FRAMING`,
  `QUESTION`, `OPTIONS`, and the `Finding {key}` line). The prompt is part of the verdict
  cache key. If it changes, every cached verdict is lost and the verdicts can shift. Rename
  the Python identifiers around it, but leave the strings as they are.
- The comment syntax `deslop-lint-disable`, `deslop-lint-disable-line`, and
  `deslop-lint-enable` stays the same. Only the prose that describes it changes.
- Leave `CHANGELOG.md` entries for past releases as they are.

## Files to update

### Output contract (the output changes, so the golden files change)

- `src/deslopper/report.py`: the `"findings"` json key, the `findings` row in the summary
  table, and the docstrings.
- `src/deslopper/cli.py`: the `finding`/`findings` noun in the run count.
- `src/deslopper/help.py`: the help text for `lint`, `check`, `--strict`, `--jev`, and
  `--no-cache`, and the examples.
- `src/deslopper/evaluate.py`: the `_broken(...)` messages for a broken baseline.
- `src/deslopper/schema/output.schema.json`: the required key and the descriptions.
- `tests/fixtures/comprehensive.json.golden` and `tests/fixtures/comprehensive.text.golden`:
  regenerate them. Do not edit them by hand. Say in the PR that the golden change is
  intended.
- `docs/qa/output-designs/sample.json`, `designs.py`, and `try.sh`: keep the QA sample in
  line with the new key.

### Code identifiers

- `src/deslopper/findings.py`: rename the module to `smells.py` and its type to `Smell`.
  Update every import.
- `src/deslopper/triage.py`, `engine.py`, `discovery.py`, `tiers.py`: rename variables,
  parameters, and docstrings. In `engine.py`, the module docstring and the docstring of
  `scan_prose` say "disable region". Change that to "exempt region".
- `.github/labeler.yml`: the path to `findings.py`.

### Tests

- `tests/test_report.py`, `test_triage.py`, `test_engine.py`, `test_cli.py`,
  `test_readme.py`, `test_output_style.py`, `test_gum.py`, `test_evaluate.py`,
  `test_e2e.py`, `test_slop_corpus.py`, `test_help.py`, `test_discovery.py`, and
  `conftest.py`: rename the identifiers and the assertions on output text.
- `scripts/jev-smoke.sh`: it reads the json output, so it needs the new key.

### Docs

- `README.md`: about 43 uses of "finding", and the line about "a disabled line" (use
  "exempt line").
- `CONTRIBUTING.md`, `AGENTS.md`, `RELEASING.md`, `skills/deslopper/SKILL.md`.
- `docs/adr/0002-styled-output-is-a-gum-layer-over-plain-output.md`: three uses.
- `CONTEXT.md`: delete the sentence "The code and output still say finding for now." from
  the Smell entry when the rename is done.

### ADR

Add `docs/adr/0003-a-match-is-a-smell.md`. Record why "smell" replaced "finding", why
"warning" was rejected (it collides with the `warn` tier), and why the json key change is
accepted as a breaking change.

## Acceptance criteria

- [ ] `git grep -iw -E "findings?"` matches only the Jev prompt strings in `triage.py`, the
      "Avoid" line in `CONTEXT.md`, the new ADR, and past `CHANGELOG.md` entries.
- [ ] `git grep -i "disable region"` matches only the "Avoid" line in `CONTEXT.md` and
      past `CHANGELOG.md` entries.
- [ ] The json output and `output.schema.json` use `"smells"`. The goldens are regenerated
      and the PR says that the change is intended.
- [ ] The Jev prompt strings are byte-for-byte unchanged. A verdict cached before the
      change is still a cache hit after it.
- [ ] `pytest -q` passes, and `deslopper lint` reports no error-tier smells.
- [ ] `CHANGELOG.md` has an unreleased section with a migration note for the json key.
- [ ] ADR 0003 exists.

## Out of scope

- Renaming the `rules` command or `rules.py` to tells. That is a separate change.
- A per-tell exempt comment. An exempt region still covers every tell.
