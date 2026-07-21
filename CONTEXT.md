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

**Finding**:
One place where a tell matched, reported at a path, line, and column. A finding is an
instance. The tell is the definition behind it.

## A tell's shape

**Tier**:
A tell's severity, either `error` or `warn` and nothing else. An `error` always fails a
lint. A `warn` fails only under strict. The set is closed.
_Avoid_: severity, level.

**Phase**:
When a tell scans a line, relative to HTML-entity masking. A `pre-entity` tell runs before
entities are blanked, a `post-entity` tell after. Only a pre-entity tell can catch a tic
spelled as an entity.

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

**Masking**:
Blanking a region to spaces before tells scan it, so no tell fires inside it. Fenced code,
inline code, front matter, and HTML entities are masked. The entity step is the one the
phase names key on.

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
The judge that lints the rewritten fixtures. Zero error-tier findings is the hard gate,
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
