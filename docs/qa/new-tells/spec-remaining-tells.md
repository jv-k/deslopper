Blocked by: #61, #66

## Problem Statement

A writer runs deslopper on a draft and gets a clean result, but a reader still sees machine-written prose. The `recommended` and `aggressive` presets miss a set of tells that other slop detectors and articles already catalogue. Some are small set phrases, such as `Then something shifted.` or `could potentially fail`. Some are a whole move, such as `Most people think caching is easy. They're wrong.`, which claims to have found what everyone else missed.

The survey in `docs/research/slop-tells-survey.md` (added in #66) lists these tells with draft regexes and their hit counts over the Django 3.2 docs. #60 (PR #64) adds the ten strongest. #61 widens fifteen existing tells. Seventeen candidates from the survey have no issue yet, so a writer who wants them must write custom tells by hand.

## Solution

Add the seventeen remaining candidates from the survey as tells. Eight have low false-positive counts and go into the `recommended` preset at tier `warn`. Nine are noisier in technical prose and go into the `aggressive` preset, where a writer opts in to stricter checks. After this, a writer who extends `recommended` gets the eight new tells by default. A writer who also extends `aggressive` gets the other nine.

Each tell reports a smell with a short message that says what is wrong and what to do instead, in the style of the existing tells.

## User Stories

1. As a writer, I want a smell on a pithy fragment such as `Dense, not cramped.`, so that I replace a slogan with a plain sentence.
2. As a writer, I want a smell on a narrative pivot such as `Then something shifted.` or `That changes everything.`, so that I state what changed instead of staging it.
3. As a writer, I want a smell on a negative listing such as `Not a bug. Not a feature. A design flaw.`, so that I name the thing directly.
4. As a writer, I want a smell on `without sacrificing` and `without compromising`, so that I state the tradeoff or show that there is none.
5. As a writer, I want a smell on urgency inflation such as `cannot be overstated` or `at a critical juncture`, so that I give the reason something is urgent.
6. As a writer, I want a smell on a stacked hedge such as `could potentially fail`, so that I keep one hedge or none.
7. As a writer, I want a smell on essay signposts such as `In conclusion,`, `In summary,`, `Key takeaways` and `Without further ado`, so that I cut the announcement and keep the point.
8. As a writer, I want a smell on business jargon such as `move the needle`, `low-hanging fruit` and `best-in-class`, so that I say the concrete thing.
9. As a writer who opts into `aggressive`, I want a smell on tutorial signposts such as `Let's dive in.` and `By the end of this guide`, so that I start with the content.
10. As a writer who opts into `aggressive`, I want a smell on `the missing piece`, `the missing link` and `the blind spot everyone missed`, so that I stop claiming a gap that others overlooked and show the gap instead.
11. As a writer who opts into `aggressive`, I want a smell on a contrarian hook such as `Most teams get this backwards.`, so that I make my claim without inventing people who disagree.
12. As a writer who opts into `aggressive`, I want a smell on contrast adverbs such as `not simply` and `rather than merely`, so that I drop the implied straw man.
13. As a writer who opts into `aggressive`, I want a smell on a straw-man tail such as `not the other way around`, so that I keep only the claim that carries information.
14. As a writer who opts into `aggressive`, I want a smell on overreach such as `the single most important` or `there's no denying`, so that I back the claim or soften it.
15. As a writer who opts into `aggressive`, I want a smell on restatement markers such as `In other words` and `Put simply`, so that I write the clear version once.
16. As a writer who opts into `aggressive`, I want a smell on a numbered lead-in such as `Three key reasons:`, so that I list the items without counting them first.
17. As a writer who opts into `aggressive`, I want a smell on figurative words that Claude overuses, such as `load-bearing` and `earns its place`, so that I use the literal word.
18. As a writer who opts into `aggressive`, I want a smell on invented concept labels such as `the context tax` or `the acceleration trap`, so that I describe the effect instead of naming it like a law.
19. As a writer of technical docs, I want honest phrases such as `the only way to` in a reference page to stay out of `recommended`, so that the default preset does not flag correct prose.
20. As a writer, I want each new smell's message to say what to do instead, so that I can fix it without reading the survey.
21. As a writer, I want a quoted example of a tell inside an exempt region to stay silent, so that docs about slop can show slop.
22. As a writer, I want example phrases in inline code to stay silent, so that docs can name a phrase without a smell.
23. As a maintainer, I want every new tell to have positive and negative test cases, so that a later change to a pattern cannot widen or narrow it unnoticed.
24. As a maintainer, I want the golden files to show the new smells, so that a reviewer sees the exact output change.
25. As a maintainer, I want each new `recommended` tell seeded in the eval corpus, so that the eval suite keeps its check that every recommended tell fires.
26. As a maintainer, I want the README tells table to list every new `recommended` tell with an example that fires it, so that users can see the full set.
27. As a maintainer, I want the repo's own Markdown to pass `deslopper lint` after the change, so that the dogfood check stays green.
28. As a maintainer, I want the survey to remain the record of where each pattern came from, so that a later tuning change can check the source.
29. As a user of the `rules` command, I want the new tells listed with their tier and message, so that I can see which tells my config turns on.
30. As a user who disables a tell in my config, I want each new tell to be disabled by its name, so that I can turn off one I disagree with.
31. As a user who extends both presets, I want no new `aggressive` tell to replace a `recommended` tell of the same name and phase, so that opting in only adds tells.

## Implementation Decisions

- All seventeen tells are data in the preset files. No engine module changes, and no new `kind`.
- The draft regexes and example phrases in the survey are the starting point for each `pattern` or `words` entry. A list of plain phrases, such as the business jargon, uses `words`. A tell with structure, such as the negative listing, uses `pattern`. Per ADR 0001, `words` entries are regex fragments.
- `recommended`, all at tier `warn`, flags `i` unless noted: `pithy-fragment` (no `i` flag, because its capital letter anchors the start of a sentence), `narrative-pivot`, `negative-listing`, `tradeoff-dodge`, `urgency-inflation`, `stacked-hedge`, `signposting` and `business-jargon`.
- `signposting` in `recommended` takes only the essay closers and openers: `in conclusion`, `in summary`, `to sum up`, `key takeaways` and `without further ado`. The tutorial phrases (`let's dive in`, `let's break this down`, `let's unpack`, `in this article, we'll`, `by the end of this guide`) go into a separate `aggressive` tell named `tutorial-signposting`. A tell of the same name and phase in a later preset replaces the earlier one, so a shared name would remove the essay closers from users who extend both presets.
- `aggressive`, all at tier `warn`: `tutorial-signposting`, `missing-piece`, `contrarian-hook`, `contrast-adverb`, `strawman-tail`, `overreach`, `restatement-marker`, `numbered-lead-in`, `claude-figurative` and `invented-concept-label`.
- `contrast-adverb` stays whole in `aggressive`, including the `less like ... and more like` form that the survey suggests could go to `warn`. One tell in one preset is simpler, and the form can move later with evidence.
- `contrarian-hook` matches only the full two-sentence form on one line, such as `Most people think X. They're wrong.`, and the `get this backwards` form. The first half alone (`most people think`) does not fire, because the survey rates it medium risk.
- `strawman-tail` takes only the low-noise tokens from the survey, such as `not the other way around`. The bare `rather than` and `instead of` tails do not fire, because the survey rates them high risk.
- `claude-figurative` leaves out `seams` and `quietly`, which the survey notes have honest technical meanings. It keeps `load-bearing`, `earns its place`, `the change lands` and `the shape of the problem`.
- `missing-piece` is in `aggressive` because no catalogue names it. The evidence is the maintainer's own observation, recorded in the survey.
- Every tell runs in the default `post-entity` phase.
- A tell name must not clash with a name in #60 or #61. Check the presets after #61 merges, before the names are fixed.
- If a new `recommended` tell fires on the repo's own Markdown, rewrite the prose if it is slop. If the hit is honest prose, narrow the pattern and say so in the PR. Do not exempt repo prose to make a tell pass.

## Testing Decisions

- A good test lints a line of text with the preset's tells and checks which smells come back. It does not test the regex string or the JSON layout.
- Seam 1 is the table of positive and negative cases per tell in the rules tests, the one PR #64 added for the survey tells. Each new tell gets every example phrase from the survey as a positive case. Each false-positive note in the survey becomes a negative case, for example `the only way to` in reference prose for `overreach` and `Everything changed in v2 is listed below` for `narrative-pivot`.
- Seam 2 is the golden fixture that covers every tell. Add one case per new tell, then regenerate the three golden files. The PR says the golden change is intended.
- Seam 3 is the eval-corpus check that every `recommended` tell fires. Seed the eight new `recommended` tells in the eval fixtures.
- Seam 4 is the README example check. Add an example for each new `recommended` tell to the README tells script and regenerate the table.
- The `aggressive` tells need seams 1 and 2 only, unless the eval suite or the README script also covers `aggressive`.
- No new seam. A test that runs every tell over a stored corpus of human prose is out of scope.
- Prior art: the survey-tell tables in the rules tests (PR #64), the existing golden test, and the eval test that asserts every recommended tell fires.

## Out of Scope

- The ten tells in #60 and the fifteen changes to existing tells in #61.
- The structural tells in the survey: one-line paragraph punches, triads, anaphora, the numbered-paragraph listicle, low sentence-length variance, false agency, fractal summaries and false ranges. They need a matcher that reads more than one line or counts across a document, which is a new `kind` and an engine change.
- Curly apostrophes in patterns, which #63 tracks for all survey tells.
- Tuning the noisier forms of the #60 tells, which #62 tracks.
- A stored human-prose corpus as a test fixture.

## Further Notes

- The survey's hit counts come from the Django 3.2 docs, which are reference prose. Zero hits there does not prove a low false-positive rate in blog posts or design notes.
- This issue touches the same golden files, eval fixtures and README table as #61, so it starts from `main` after #61 merges.
- #66 adds the survey to the repo. Until it merges, the survey is on the `docs/slop-tells-survey` branch.
