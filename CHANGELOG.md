## 0.2.0 (2026-07-17)
- chore: updated package.json, updated pyproject.toml, updated src/deslopper/__init__.py, updated CHANGELOG.md, bumped 0.1.1 -> 0.2.0
- Merge pull request #14 from jv-k/fix/edge-hardening
- refactor(config): merge tells through one copying helper
- fix(report): escape delimiters in the github annotation path
- fix(discovery): skip a tracked file deleted from the worktree
- fix(config): copy added tells so resolve does not mutate the caller
- Merge pull request #13 from jv-k/fix/glob-and-scanner-edges
- fix(engine): pair a backtick run only with an equal-length run
- fix(discovery): match globs by segment and show out-of-root paths absolutely
- Merge pull request #12 from jv-k/fix/review-findings
- fix(engine): guard disable-line against unknown suffixes too
- refactor: dedup the exclude floor and correct a docstring
- fix(engine): bound fences to CommonMark and stop a disable suffix disabling the file
- fix(discovery): resolve explicit relative paths against the cwd
- fix(config): let files.exclude narrow the default excludes
- Merge pull request #11 from jv-k/refactor/deepen-modules
- Merge pull request #10 from jv-k/docs/domain-model
- refactor(tiers): collapse the two failure sets into one
- fix(rules): reject an unknown tier at compile time
- refactor(tiers): read tier behaviour from one table
- refactor(discovery): move the work-list behind resolve_worklist
- refactor(engine): split the prose scanner from the tell runner
- docs(context): add the domain glossary and the words-are-regex ADR
- Merge pull request #9 from jv-k/chore/adopt-ver-bump
- chore(release): address review — restore the tree and branch gates
- chore(release): cut releases with ver-bump
- Merge pull request #8 from jv-k/chore/release-plumbing
- docs(releasing): address review — name the bump scripts
- docs(changelog): repair the 0.1.2 section
- fix(scripts): gate the release on package.json too
- Merge pull request #7 from jv-k/feat/id-label-tell
- fix(rules): reject a group-indexing pattern that has no groups
- feat(rules): add id-label tell
- Merge pull request #6 from jv-k/fix/delve-proper-noun-false-positive
- test(rules): address review — load the preset through the app's loader
- fix(preset): stop filler-verb flagging Delve the debugger
- chore: updated package.json, updated CHANGELOG.md, bumped 0.1.1 -> 0.1.2
- feat(rules): add middle-dot tell (#5)

# Changelog

## 0.1.2 (unreleased)

- `middle-dot`: flag the interpunct and bullet separators, both as characters and as the
  HTML entity spellings. Error tier.
- `id-label-lead`: flag the `G1` or `NG2` id label stapled to a list item. Warn tier.
- `filler-verb` leaves `Delve` the Go debugger alone, and still flags `delve` the verb.
- A tell whose kind reads capture groups by number (`bold-bullet`, `id-label`) now reports a
  malformed pattern as a config error at compile time, instead of failing mid-lint.
- Releases are cut with [ver-bump](https://github.com/jv-k/ver-bump), driven by `.ver-bumprc`,
  the same way the engineering-playbook cuts its own. `scripts/bump.py`, `bump-release.sh`
  and `release.sh` are gone. `pnpm bump-release` runs the gates and hands off. The version
  files are checked by a test now, so drift fails in CI rather than after the tag is public.

## 0.1.1
- Test coverage: a realistic slop-corpus regression test and subprocess end-to-end tests
  that drive `python -m deslopper` directly.
- `pnpm bump-release`: one task that bumps the version, retitles this changelog, commits,
  and releases.

## 0.1.0

- The deterministic lint core, ported byte-for-byte from the engineering-playbook scripts.
- The bundled `recommended` rule set (twelve tells, error and warn tiers).
- `deslopper.config.json` with `extends`, `tells.add`, `tells.override`, `tells.disable`,
  `strict`, and `files`, keyed by (name, phase).
- Commands: `lint`, `check`, `rules`, `init`.
- Output formats: text, github, json. Exit codes 0, 1, 2.
- Built-in presets are flat `<name>.json` files in `src/deslopper/presets/`. `extends`
  accepts multiple built-in presets, resolved left to right.
- Community infra: a contributing guide, issue and PR templates, a labeler, and commit and
  PR title linting.
- File discovery and the scanner now cover `.mdx`. Top-level ESM `import` and `export` lines
  are skipped. JSX that wraps prose is still linted.
