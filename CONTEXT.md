# deslopper

deslopper is a deterministic linter that flags the tics of machine-generated prose in
Markdown. This glossary fixes the words the project uses for its own parts.

## Core

**Tell**:
A named detector for one machine-generated writing tic, matched line by line against
prose. The central object of the project.
_Avoid_: rule. The `rules` command and `rules.py` keep the old word for now, but the thing
they act on is a tell.

**Slop**:
The machine-generated writing tics that tells catch. To de-slop is to remove them. The
tool is named for the act.

**Preset**:
A named, built-in bundle of tells, shipped as one `<name>.json` file and opted into with
`extends: ["deslopper:<name>"]`. `recommended` is the default.
_Avoid_: rule set, ruleset.

**Active tells**:
The tells that a project's lint uses: the tells from its presets, plus the tells it adds,
with its overrides applied, minus the tells it disables.
_Avoid_: ruleset, enabled rules.

**Smell**:
One place where a tell matched, reported at a path, line, and column. A smell is an
instance. The tell is the definition behind it. A smell has the tier of its tell, so there
are error smells and warn smells. Triage can judge a smell worth keeping, and it is still a
smell.
_Avoid_: finding, warning, match. The code and output still say finding for now. Warning
collides with the `warn` tier.

## A tell's shape

**Tier**:
A tell's severity, either `error` or `warn` and nothing else. An `error` always fails a
lint. A `warn` fails only under strict. The set is closed.
_Avoid_: severity, level.

**Strict**:
The lint mode in which a `warn` smell fails the lint too. Off by default. It changes
which smells fail, never which smells are reported.
_Avoid_: pedantic, warnings-as-errors.

**Phase**:
When a tell scans a line, relative to HTML-entity masking. A `pre-entity` tell runs before
entities are blanked, a `post-entity` tell after. Only a pre-entity tell can catch a tic
spelled as an entity.

**Tell identity**:
A tell is identified by its name and its phase together, written `name@phase`. Two tells
can share a name if their phases differ. They are still two tells. The name alone is
enough only when one tell has it.

**Scope**:
How many times a tell reports on one line: `all` for every match, `first` to stop after
the first.

**Kind**:
The matcher a tell compiles to. `regex` is the default. The `bold-bullet` and `id-label`
kinds read their pattern's capture groups by number.

**Pattern and words**:
The two ways to write a tell's match. `pattern` is a regex. `words` is a list of regex
fragments joined into one boundaried alternation, so an entry like `utili[sz]es?` is a
fragment, not a literal string.
_Avoid_: calling `words` a word list. The entries are regex.

## Scanning

**Prose line**:
A line that tells scan. Every line is a prose line unless it is skipped.

**Skipped line**:
A line that no tell scans. Front matter, fenced code, MDX import and export lines, and
exempt regions are skipped.

**Masking**:
Blanking part of a prose line to spaces before tells scan it, so no tell fires inside that
part. The rest of the line is still scanned. Inline code and HTML entities are masked. The
entity step is the one the phase names key on.

**Exempt region**:
Lines that the author takes out of the scan with a `deslop-lint-disable` comment, up to the
next `deslop-lint-enable`. An exempt line is one line taken out with
`deslop-lint-disable-line`. An exemption covers every tell. It cannot exempt one tell only.
_Avoid_: disable region, suppression. Disable means removing a tell from the config.

**Disable**:
To remove a tell from the project's set in the config, so that no file is scanned for it.
_Avoid_: using disable for an exempt region.

## Output

**Plain output**:
The output that every run can produce: smell lines, `github` annotations, or the
`json` payload. Editors, CI, models and the golden files read it, so it is a contract.

**Attended run**:
A run where a person is assumed to watch a terminal, so deslopper draws a styled view
through gum in place of the plain text. Whether a run is attended is decided from the
environment. The person cannot pick it with a flag.
_Avoid_: interactive, TTY mode, pretty mode.

## Triage

**Triage**:
The opt-in pass, `lint --jev`, that asks Jev about each smell after the scan. It
annotates and never gates: the exit code is the scan's alone.
_Avoid_: classification, labelling.

**Verdict**:
Jev's answer for one smell, `keep` or `rewrite`, with the probability of that answer. A
smell without one renders exactly as before.
_Avoid_: label, score.

**Verdict cache**:
The verdicts kept on disk between `--jev` runs. A smell is not sent to Jev again while
its tell, column, and context lines are unchanged. The line number is not part of the key.
`--no-cache` skips it.
_Avoid_: memo, history.

## The eval

**Eval**:
A run of `deslopper eval` that judges a rewrite command: seed a sandbox with the
fixtures, run the command over it, judge the result.
_Avoid_: test, benchmark. The pytest suite tests deslopper. An eval judges someone
else's rewrite pass.

**Sandbox**:
The temporary directory an eval seeds with the fixtures and hands to the rewrite
command. Made fresh per run and removed unless kept for inspection.

**Efficacy**:
The judge that lints the rewritten fixtures. Zero error-tier smells is the hard gate,
and the warn count must land strictly below the raw baseline.

**Preservation**:
The judge that compares each fixture's digest from before and after the rewrite. Any
difference fails the run.

**Digest**:
The extract of a fixture's protected content the preservation judge compares: fenced
code and front matter verbatim, the heading outline, table rows with cells normalised,
and link destinations in order.

**Baseline**:
The lint result of the raw fixtures, taken before the rewrite runs. No errors or no
warnings in it means the harness itself is broken, and the eval aborts.

**Plainness**:
The eval's third judge, a reported score in 0..1 of how plainly a fixture reads, asked
of Jev (the `typesafe-ai/jev` evaluation model behind the Vercel AI Gateway) before and
after the rewrite so the line shows how far the text moved. Opt-in, reported, never
gated: it cannot change the verdict or the exit code.
_Avoid_: readability, quality.
