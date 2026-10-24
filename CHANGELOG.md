# Changelog

## 1.7.0

- `deslopper update` upgrades deslopper with the tool that installed it: Homebrew, pipx,
  or uv. For any other install it prints the command to run and changes nothing.
  `--dry-run` shows the command without running it. The README has a new Update section.
- The lint and check view ends with a summary table drawn by `gum table`, as wide as the
  rules above it: the findings, errors, warnings, and after a `--jev` run the rewrite and
  keep verdicts. A `--jev` run adds a second table with what Jev cost: a `this run` row
  with the verdicts asked for, their tokens and cost, and a `cache saved` row with the
  verdicts the cache answered and what they cost when Jev first gave them. The tables
  round costs to two significant figures.
- Each cached verdict now keeps its share of the tokens and cost of the request that
  answered it. The plain summary line ends with `· saved T tokens, $C`, and the `jev`
  object in the output schema gains required `saved_tokens` and `saved_cost` fields. A
  verdict cached by 1.6.0 has no share, so the table shows its saving as `unknown`.
- The README contents lists the main sections only.

## 1.6.0

- `lint --jev` keeps each verdict on disk, in `$XDG_CACHE_HOME/deslopper/jev` or
  `~/.cache/deslopper/jev`, and reuses it. A finding whose line and neighbours have not
  changed is not asked again, even after it moves down the file, and a file with every
  finding cached sends no request. `--no-cache` asks Jev about every finding again. The
  summary, the gum view, and the `json` payload count the cached verdicts: the `jev`
  object in the output schema gains a required `cached` integer.
- The help screens, the eval report, and the status lines for `init` and errors are drawn
  by gum on a terminal, like the lint view. The help keeps its rainbow wordmark, and its
  plain text is unchanged. On a terminal, eval draws the findings left after the rewrite
  with the lint view.
- The hand-written colour palette and its `FORCE_COLOR` gate are gone. gum reads
  `NO_COLOR` and `CLICOLOR_FORCE`, and there is no other source of colour.
- The README leads with a demo GIF of the new view and a live Jev run. The screenshots
  workflow installs gum, checks that Jev answers before it records, and sizes the help
  screenshot to fit.

## 1.5.0

- On a terminal with [gum](https://github.com/charmbracelet/gum), `lint` and `check` draw
  one view: a header, a section per file, each tell once with its fix, then every place it
  fired, with the line, the caught words highlighted, and a caret under them. With `--jev`,
  each place starts with Jev's rating, and a spinner names each file while Jev reads it.
  Without gum, a terminal gets the plain output and one install hint. Piped, `github`, and
  `json` output are unchanged.
- `--jev` replaces `--triage`, which still works as a hidden alias.
- `--format json` writes only its payload. With `--jev`, a `jev` object carries the totals
  and any failed requests, and the output schema describes it.
- A folder argument, such as `deslopper lint docs/`, lints the files a bare run would lint
  in that folder. It used to report the folder as unreadable.
- Findings on one line list in column order.
- The README calls deslopper "A slop linter for Markdown", and adds a contents list, a
  guide to fixing slop with an LLM, and install steps that work while the package is not
  on PyPI.
- The release workflow can run for an existing tag (`gh workflow run release.yml -f
  tag=vX.Y.Z`), and the Homebrew tap now follows each release.

## 0.2.0 (2026-07-17)

Carries everything that was staged for 0.1.2, which was bumped but never tagged.

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
- The scanner splits in two. `scan_prose` owns the block structure, which is front matter,
  fences, MDX ESM lines, disable regions, and masking, and the tell runner reads the prose
  lines it yields. The block rules are testable on their own for the first time.
- File discovery sits behind one `resolve_worklist` call that owns the discovery root, so
  the command line no longer threads it.
- `tier` is a closed set of `error` and `warn`, read from one table. An unknown tier is a
  config error at compile time rather than a finding that can never fail a lint.
- Fences follow the CommonMark block rules: at most three spaces of indent, a bare closing
  run of the same character, and no backtick inside a backtick fence's info string. Each of
  those used to open or close a block wrongly and skip the rest of the file.
- A `deslop-lint-disable` directive with an unknown suffix, such as the `-next-line` spelling
  borrowed from eslint, no longer switches off the rest of the file.
- Inline code pairs a backtick run only with a run of the same length, so prose between two
  mismatched runs is linted rather than masked as code.
- Globs match by path segment. `*` stops at a slash and `**` spans zero or more segments, so
  `docs/*.md` no longer reaches nested files and `docs/**/*.md` no longer misses top-level
  ones.
- `files.exclude` narrows the defaults instead of only widening them. `node_modules` and
  `.git` stay excluded, and a config that replaces the list frees `vendor` and `reference`.
- A relative path on the command line resolves against the working directory rather than the
  discovery root, so linting from a subdirectory reads the file that was named.
- A file outside the discovery root reports an absolute path, and the github annotation
  escapes the delimiters a path can carry.
- A tracked file deleted from the worktree is skipped rather than reported unreadable.
- `resolve()` copies the tells it is given, so it no longer mutates the caller's config.

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
