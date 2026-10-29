# Survey of slop tells deslopper does not catch yet

This survey reads the rule files and source of other slop detectors, plus the articles they
cite, and lists tells that the `recommended` and `aggressive` presets miss. It was compiled
on 2026-10-28.

Each candidate has a kebab-case name, example phrases, a draft regex (or a note on why a
regex struggles), a false-positive estimate for technical docs, a suggested tier, and its
sources. Example phrases sit in inline code so the linter skips them.

The engine matches one line at a time after it strips code. So a tell that spans two
paragraphs, or that depends on sentence length or repetition across a document, is out of
reach for a single pattern. Such tells are marked structural.

## How the regexes were checked

Every draft regex below was run against a few positive and negative examples, then against
two corpora:

- The deslopper `docs/` folder and `README.md` (688 lines).
- The Django 3.2 docs (`docs/**/*.txt`, 141,541 lines, written before 2022 and so before
  chatbot prose). This stands in for careful human technical writing.

The "Django hits" figure in each entry is the count of matching lines in that corpus. Zero
hits in 141k lines is a good sign but does not prove a low false-positive rate, since Django
docs are reference prose, not blog posts or design notes.

## The "nobody noticed the gap" family

The move: the text talks about something abstract, then claims to have spotted what others
missed. The claim of a gap carries the weight, and the content after it is often ordinary.
Several catalogues name it:

<!-- deslop-lint-disable -->
- tbhb/vale-ai-tells has a rule for it, `FalseExclusivity.yml`, at error level, with the
  message "State the point directly without claiming insider knowledge".
- tropes.fyi files it under false suspense ("Here's what most people miss") and under "The
  Truth Is Simple" ("none of them is the real story. The real story is...", described as
  "claiming privileged insight while waving away everything before it").
- Jodie Cook's ban list groups it as "false directness and setup phrases".
- A study of 500 AI-generated LinkedIn posts found that 27% opened with the template "I
  [achievement]. But here's what nobody tells you about [topic]", and 38% with "Most people
  think [belief]. They're wrong."
- Ruben Hassid lists "What nobody tells you is..." and "The real work isn't X. It's Y."
- stop-slop lists "The uncomfortable truth is", "The real [X] is", and the structure "[X]
  isn't the problem. [Y] is."
<!-- deslop-lint-enable -->

### false-exclusivity

Claims that others fail to see or say the thing.

- Examples: `Nobody talks about the cost.`, `Here's what nobody tells you about caching.`,
  `What no one tells you is`, `The part everyone misses`, `What most people get wrong`,
  `No one is talking about this.`
- Regex (flags `i`):
  `\b(?:what |the (?:part|thing|bit) )?(?:nobody|no one|no-one|few people|most people|everyone)(?: is)? (?:talks? about|talking about|tells? you|mentions?|warns? you(?: about)?|discusses|notices|realizes|gets? (?:this |it )?wrong|misses|overlooks|forgets|skips)\b`
- False-positive risk: low. Django hits: 0. The verb list keeps out plain uses such as
  `No one can write to the file`.
- Tier: warn in `recommended`.
- Sources: tbhb/vale-ai-tells `FalseExclusivity.yml`, tropes.fyi, Jodie Cook ban list,
  Adrian Vega's LinkedIn study, Ruben Hassid.

### hidden-truth

A noun phrase that promises a concealed truth.

- Examples: `The quiet truth is that tests rot.`, `the hidden cost of retries`,
  `The uncomfortable truth:`, `the dirty little secret`, `the inconvenient truth`.
- Regex (flags `i`):
  `\bthe (?:uncomfortable|inconvenient|unspoken|hidden|quiet|ugly|dirty(?: little)?|open|simple|hard|brutal) (?:truth|secret|reality|cost|costs)\b`
- False-positive risk: low for `truth`, `secret`, `reality`. Medium for `hidden cost`, which
  is a real term in performance writing. Django hits: 0.
- Tier: warn. Move `hidden cost(s)` to `aggressive` if it proves noisy.
- Sources: tbhb/vale-ai-tells `FalseExclusivity.yml` (lists `the hidden cost`,
  `the uncomfortable truth`, `the unspoken reality`, `the dirty secret`,
  `the elephant in the room`), stop-slop `phrases.md`.

### missing-piece

The claim that the text supplies the one part everyone lacked.

- Examples: `This is the missing piece.`, `the missing link`, `the gap nobody noticed`,
  `the blind spot everyone missed`.
- Regex (flags `i`):
  `\b(?:the|a) missing (?:piece|link|ingredient|layer)\b|\bthe (?:gap|blind spot) (?:nobody|no one|everyone|most people|we all) (?:noticed|saw|missed|ignored|overlooked)\b`
- False-positive risk: low to medium. `missing piece` appears in puzzle and data-gap prose.
  Django hits: 0.
- Tier: `aggressive`. No catalogue lists it by name, so the evidence is weaker than for
  `false-exclusivity`.
- Sources: the maintainer's own observation. Related to tropes.fyi "The Truth Is Simple".

### real-problem-reframe

Moves the reader's attention from a stated problem to a "real" one. This is the
negation-pivot applied to a diagnosis.

- Examples: `The real problem isn't speed, it's trust.`, `Latency isn't the bottleneck.`,
  `It was never about the code.`, `The question isn't X. It's Y.`
- Regex (flags `i`):
  `\bthe (?:real|actual|true|bigger|deeper) (?:problem|issue|question|bottleneck|story|work|risk|lesson)(?: here)? (?:isn'?t|is not|wasn'?t|was not)\b|\b[\w-]+ (?:isn'?t|is not|wasn'?t) the (?:real |actual )?(?:problem|bottleneck|issue|point)[.,:]|\b(?:it|this) (?:was|is) never (?:really )?about\b`
- False-positive risk: low. The regex needs the negated form. The plain
  `the real problem is` stays out, because debugging notes use it honestly (Django has one
  such line). Django hits: 0.
<!-- deslop-lint-disable -->
- Tier: warn.
- Sources: stop-slop `structures.md` ("[X] isn't the problem. [Y] is.", "The answer isn't X.
  It's Y.", "The question isn't X. It's Y."), Ruben Hassid ("The real work isn't X. It's
  Y."), slop-guard `closing_aphorism.py` (`^the (real|true|actual|biggest|...)`), pen2profit
  ("It was never about the thing" is cited in search results but was not on the page when
<!-- deslop-lint-enable -->
  fetched).

### contrarian-hook

`Most people think X. They're wrong.` The opener sets up a belief nobody in the text holds,
then knocks it down.

- Examples: `Most people think caching is easy. They're wrong.`,
  `Most teams get this backwards.`
- Regex: partly lexical.
  `\b(?:most people|most teams|most developers|everyone)\s+(?:thinks?|assumes?|believes?)\b[^.!?]{0,80}[.!?]\s+(?:they'?re|they are|that'?s) wrong\b`
  catches the two-sentence form when both sentences sit on one line.
- False-positive risk: low for the full form. The first half alone (`most people think`) is
  medium. Django hits: 0 for the full form.
- Tier: `aggressive`.
- Sources: Adrian Vega's LinkedIn study (Pattern A, 38% of openers), stop-slop "Lazy
  extremes".

## Staging and false suspense

### false-suspense

A phrase that announces a reveal before an ordinary point. The current `throat-clearing`
tell does not include any `here's` form.

- Examples: `Here's the thing:`, `Here's the kicker.`, `Here's where it gets interesting.`,
  `Here's why this matters.`, `Here's what I learned.`, `The kicker`.
- Regex (flags `i`):
  `\bhere'?s (?:the (?:thing|kicker|catch|deal|twist|truth|reality|secret|rub|part)|where (?:it|things) gets? (?:interesting|tricky|weird|good)|what (?:most|nobody|no one|everyone|few|I (?:learned|found|mean|noticed)|you need to know|matters)|why (?:this|that|it) matters)\b|\bthe kicker\b`
- False-positive risk: low. `Here's how` and `Here's the output` stay out. Django has 17
  lines with `here's the`, and none match. `Here's the catch` is the riskiest branch.
<!-- deslop-lint-disable -->
- Tier: warn. This is the top non-gap candidate: the LinkedIn study found `Here's the thing`
  in 170 of 500 posts.
- Sources: tropes.fyi "Here's the Kicker", stop-slop `phrases.md`, slop-guard
<!-- deslop-lint-enable -->
  `slop_phrase.py` (`here's the thing`, `this is where things get interesting`),
  tbhb/vale-ai-tells `AffirmativeFormulas.yml`, humanizer section 4, Adrian Vega.

### rhetorical-self-answer

`The X? Y.` A question nobody asked, answered at once.

- Examples: `The result? Devastating.`, `The catch? It only runs on Linux.`,
  `The worst part? Nobody saw it coming.`
- Regex (flags `i`):
  `(?:^|[.!?:]\s+)(?:and |but )?the (?:result|outcome|catch|kicker|twist|problem|answer|fix|reason|truth|reality|best part|worst part|scary part|hard part|irony|takeaway|upshot|difference|cost|payoff|secret|trick|lesson|verdict|bottom line)\?\s+[A-Z\d]`
- False-positive risk: low. The anchor keeps out `What is the result? See below.` Django
  hits: 0.
- Tier: warn.
- Sources: tropes.fyi "The X? A Y.", tbhb/vale-ai-tells `RhetoricalSelfAnswer.yml` (44
  nouns), stop-slop "Questions answered immediately", Jodie Cook ("The best part?").

### emphasis-crutch

A line that tells the reader to feel the weight of the previous one.

- Examples: `Let that sink in.`, `Read that again.`, `Full stop.`, `Make no mistake`,
  `I'll say it again:`, `Yes, really.`
- Regex (flags `i`):
  `\blet that sink in\b|\bread that again\b|\bfull stop\.|\bmake no mistake\b|\bI'?ll say it again\b|\bthink about that for a (?:second|moment)\b|\byes, really\b`
- False-positive risk: low. `Use a full stop` does not match because the regex needs the
  period. Django hits: 0.
- Tier: warn.
- Sources: Adrian Vega (`Let that sink in` 28x human rate, `Read that again` 22x,
  `Full stop.` 14x), stop-slop "Emphasis Crutches", tbhb/vale-ai-tells `MicDrop.yml` and
  `AbsoluteAssertions.yml`, humanizer section 2.

### staged-candor

A performed moment of honesty before a routine claim. It is a frequent Claude tic.

- Examples: `And honestly?`, `Honestly? It depends.`, `Honest take:`, `Let's be honest,`,
  `To be frank`, `If I'm being honest`, `The honest answer`.
- Regex (flags `i`):
  `(?:^|[.!?]\s+)(?:and |but )?(?:honestly|frankly|look|real talk|truthfully)\?|\b(?:let'?s be honest|to be (?:honest|frank)|if I'?m (?:being )?honest|I'?ll be honest|in all honesty|(?:(?:the|my|an) )?honest (?:take|assessment)|(?:the|my) honest (?:answer|truth))\b`
- False-positive risk: low. `He answered honestly` does not match. Django hits: 0.
- Tier: warn.
- Sources: Adrian Vega (`And honestly?` 15x), humanizer section 4 ("Honestly?", "Real
  talk"), krishnasunkam/vale-ai-tells `VirtueHonest.yml`, tropes.fyi "False Vulnerability",
  Jodie Cook, HN thread on "How to stop Claude from saying load-bearing" (`Honest take:`,
  `The honest caveat`).

### narrative-pivot

A turn in a story that stands in for the cause.

- Examples: `Then something shifted.`, `Everything changed.`, `That changes everything.`,
  `And then it clicked.`, `The penny dropped.`
- Regex (flags `i`):
  `\b(?:something|everything) (?:shifted|changed|clicked)(?=[.!]|$)|\b(?:this|that) changes? everything\b|\band then it (?:clicked|hit me)\b|\bthe penny dropped\b`
- False-positive risk: low. The lookahead keeps out
  `Everything changed in v2 is listed below`. Django hits: 0.
- Tier: warn.
- Sources: tbhb/vale-ai-tells `NarrativePivots.yml`, slop-guard `slop_phrase.py` and
  `tone_marker.py` (`something shifted`, `then something interesting happened`).

### mic-drop

A short closing line that grades the point instead of adding to it.

- Examples: `That's the whole point.`, `And that's okay.`, `That's the beauty of it.`,
  `This is what good tooling looks like.`, `It matters.` (alone on a line).
- Regex (flags `i`):
  `\b(?:that'?s|this is|which is) (?:exactly )?the (?:whole |entire |real )?point\b|\b(?:that'?s|this is) the (?:beauty|power|magic) of\b|\b(?:this|that) is what [^.!?]{1,40} (?:actually |really )?looks like\b|\band that'?s (?:okay|fine|the point|the whole point)\.|^\s*(?:it|this|that) (?:matters|works|scales|compounds|shows)\.\s*$`
- False-positive risk: low for the set phrases. Django hits: 0. tbhb/vale-ai-tells has a
  much wider `MicDrop.yml` (bare `Not X.`, `X over Y.`, `[Noun] is a [noun].`) that would be
  noisy here.
- Tier: warn for the regex above. The wider short-sentence forms belong in `aggressive`.
- Sources: tbhb/vale-ai-tells `MicDrop.yml`, `PointVerdict.yml`, `AffirmativeFormulas.yml`,
  stop-slop "Dramatic Fragmentation", humanizer section 2.

### pithy-fragment

A verbless two-beat fragment as its own sentence.

- Examples: `Dense, not cramped.`, `Simple, yet effective.`, `Useful, but incremental.`
- Regex (no `i` flag, so the capital anchors the start of a sentence):
  `(?:^|[.!?]\s+)[A-Z][a-z]+, (?:not|never|yet|but) [a-z]+\.`
- False-positive risk: low. Django hits: 0.
- Tier: warn.
- Sources: slop-guard `pithy_fragment.py`, tbhb/vale-ai-tells `MicDrop.yml` ("X, not Y."),
  krishnasunkam/vale-ai-tells `NeverTag.yml`.

## Contrast formulas

The `not-just-x-but-y` tell catches one form. The sources agree that the contrast family is
the most common current tell. The Economist analysis and Pangram figures (as reported in
secondary coverage) put it at about three times the human rate, and Graphite reports
corrective framing at about 12 times the human rate in GPT-6 Astra.

### negation-pivot

`It's not X. It's Y.` and its split and inverted forms.

- Examples: `It's not a bug. It's a feature.`, `This isn't about speed, it's about trust.`,
  `Not because it is slow. Because it is wrong.`,
  `You don't need more tests. You need better ones.`
- Regex (flags `i`):
  `\b(?:it|this|that|they|these)(?:'s|'re| is| are| was| were)? ?(?:not|n't)\b[^.!?]{1,60}[.,;:]\s*(?:it|this|that|they)(?:'s|'re| is| are| was) (?:a|an|the|about|just|simply|really|actually|more|less|what|how|why)\b|\bnot because\b[^.!?]{1,80}[.,]\s+because\b|\byou don'?t need (?:more |another |a |an )?[^.!?]{1,40}[.,]\s+you need\b`
- False-positive risk: medium. Without the word list after the second `it's`, the pattern
  flagged the human sentence `It is not set by default. It is read from the env.` With the
  list, Django hits: 0.
- Tier: warn. Consider folding it into `not-just-x-but-y` under one name.
- Sources: Wikipedia "Not X, but Y", tropes.fyi "Negative Parallelism", slop-guard
  `setup_resolution.py` (two regexes this draft is based on), stop-slop "Binary Contrasts",
  tbhb/vale-ai-tells `ContrastiveFormulas.yml`, Ruben Hassid ("You don't need more X. You
  need Y."), Adrian Vega (`It's not about X, it's about Y` 17x).

### negative-listing

`Not X. Not Y. Just Z.` A countdown of negations before the point.

- Examples: `Not a bug. Not a feature. A design flaw.`,
  `No config, no flags, just one binary.`
- Regex (flags `i`):
  `\b(?:no|not) [^.,;!?]{1,30}[.,] (?:no|not) [^.,;!?]{1,30}[.,] (?:just|only|but|a|an|the)\b`
- False-positive risk: low. Django hits: 0.
- Tier: warn.
- Sources: tropes.fyi "Not X. Not Y. Just Z.", Wikipedia ("no ..., no ..., just ..."), <!-- deslop-lint-disable-line -->
  stop-slop "Negative Listing", tbhb/vale-ai-tells `ContrastiveNegation.yml`.

### contrast-adverb

Definition by contrast with a softening adverb. Graphite measured these at 43x to 187x the
human rate.

- Examples: `It is not simply a cache.`, `rather than merely storing it`,
  `less like a tool and more like a colleague`, `is genuinely useful`.
- Regex (flags `i`):
  `\b(?:rather than|not|isn'?t|is not) (?:merely|simply|solely)\b|\bless like an? [^.,;]{1,40} and more like\b|\bis genuinely\b`
- False-positive risk: medium. Django hits: 4 (`rather than simply joining`,
  `is not simply Python`). Human writers use `not simply` with care.
  `less like ... and more like` is the cleanest branch (Graphite: 125 Opus 5 hits against 1
  human).
- Tier: `aggressive`, except `less like ... and more like`, which can go to warn.
- Sources: Graphite "AI Tells" research, Wikipedia "Y rather than X".

### strawman-tail

The "not X" half moved to the end of the clause after a comma.

- Examples: `the reader walks the index, rather than walking the whole tree`,
  `it keeps one copy, not one per caller`,
  `the join goes from chunk to blob, not the other way around`.
- Regex: tbhb/vale-ai-tells `StrawmanContrast.yml` has five tokens with measured corpus
  hits. The tightest two are
  `, not (?:the other way(?: around| round)?|the reverse|the inverse|the opposite|vice versa)\b`
  and `, not (?:one|once) (?:per|for each|for every)\b`.
- False-positive risk: medium to high for the `rather than` and `instead of` tails. Bare
  `rather than` appears on 275 Django lines. The reversal tail measured zero in the Go and
  Python standard libraries, per the rule's own comments.
- Tier: `aggressive`.
- Sources: tbhb/vale-ai-tells `StrawmanContrast.yml`, humanizer section 1 ("a clipped
  negative tail").

### tradeoff-dodge

The claim that a gain costs nothing.

- Examples: `fast without sacrificing safety`, `without compromising quality`.
- Regex (flags `i`): `\bwithout (?:sacrificing|compromising)\b`
- False-positive risk: low to medium. `without losing` and `without requiring` are also on
  Graphite's list but are common in plain technical prose (`without losing data`), so they
  stay out. Django hits: 0.
- Tier: warn.
- Sources: Graphite "AI Tells" research ("Avoiding tradeoffs").

## Inflation and importance

### importance-flag

A sentence that says something matters instead of showing why.

- Examples: `This matters because`, `Why this matters`, `That distinction matters.`,
  `matters more than ever`.
- Regex (flags `i`):
  `\b(?:this|that|which|it) (?:\w+ )?matters because\b|\bwhy (?:this|that|it) matters\b|\b(?:this|that|the) (?:distinction|difference|nuance|detail|choice|framing) matters\b|\bmatters more than (?:ever|you think)\b`
- False-positive risk: low. `The order matters for hashing` does not match. Django hits: 0.
- Tier: warn.
- Sources: Graphite (`matters because` 132x to 357x, `distinction matters` with zero human
  hits), Wikipedia ("distinction [matters/is important] because"), stop-slop ("This matters
  because"), tbhb/vale-ai-tells `Metacommentary.yml`.

### urgency-inflation

World-historical stakes for an ordinary subject.

- Examples: `cannot be overstated`, `more important than ever`,
  `has never been more critical`, `at an inflection point`, `at a critical juncture`,
  `the stakes have never been higher`.
- Regex (flags `i`):
  `\bcan(?:not|'?t) be (?:overstated|understated|emphasi[sz]ed enough)\b|\bmore (?:important|critical|relevant|urgent|essential|vital) than ever\b|\bha(?:s|ve) never been more\b|\bat (?:a|an) (?:crossroads|inflection point|critical juncture|pivotal moment|turning point)\b|\bthe stakes (?:have never been|are|couldn'?t be) (?:higher|enormous|immense)\b`
- False-positive risk: low. Django hits: 0. Catch rate in technical docs is lower than in
  blog prose.
- Tier: warn.
- Sources: tbhb/vale-ai-tells `UrgencyInflation.yml`, tropes.fyi "Grandiose Stakes
  Inflation".

### overreach

Absolute claims that nothing in the text supports.

- Examples: `the only way to`, `the single most important`, `above all else`,
  `there's no denying`.
- Regex (flags `i`):
  `\bthe only (?:way to|real solution|way forward)\b|\bthe single most\b|\barguably the most\b|\babove all else\b|\bthere(?:'s| is) no denying\b`
- False-positive risk: medium. Django hits: 3, all `the only way to` in honest docs.
  Graphite reports `single most` and `arguably the most` only in Opus 5 output against GPT-6 Astra.
- Tier: `aggressive`.
- Sources: tbhb/vale-ai-tells `AbsoluteAssertions.yml`, Graphite, stop-slop "Lazy extremes".

### stacked-hedge

Two hedges where one would do.

- Examples: `could potentially fail`, `might possibly`, `may arguably`.
- Regex (flags `i`):
  `\b(?:could|may|might|can) (?:potentially|possibly|arguably|perhaps|conceivably)\b`
- False-positive risk: low. Django hits: 1 (`could potentially be multiple`).
- Tier: warn.
- Sources: humanizer section 9, tbhb/vale-ai-tells `StackedHedges.yml`.

## Announcing structure

### signposting

The text announces its own structure or conclusion.

- Examples: `In conclusion,`, `In summary,`, `To sum up`, `Key takeaways`, `Let's dive in.`,
  `Let's break this down`, `Let's unpack`, `Without further ado`, `In this article, we'll`,
  `By the end of this guide`.
- Regex (flags `i`):
  `\b(?:in conclusion|in summary|to sum up|to recap|key takeaways?|let'?s (?:dive|delve) in(?:to)?|let'?s (?:break (?:this|it) down|unpack|explore)|without further ado|in this (?:article|post|guide|section),? (?:we'?ll|we will|I'?ll)|by the end of this (?:article|post|guide|tutorial))\b`
- False-positive risk: medium. Django hits: 3 (`By the end of this tutorial`, `to recap`,
  `let's dive in`), all in tutorial prose.
- Tier: warn for `in conclusion`, `in summary`, `key takeaways`, `without further ado`.
  `aggressive` for the tutorial phrases.
- Sources: Wikipedia "Section summaries", tropes.fyi "The Signposted Conclusion" and "Let's
  Break This Down", slop-guard `slop_phrase.py`, tbhb/vale-ai-tells
  `StructureAnnouncements.yml` and `OpeningCliches.yml`.

### restatement-marker

A phrase that says the same point a second time.

- Examples: `In other words`, `Put simply`, `Simply put`, `Put differently`,
  `To put it another way`, `What this means is`.
- Regex (flags `i`):
  `\b(?:in other words|put simply|simply put|put differently|said differently|to put it (?:simply|another way)|what (?:this|that) means is)\b`
- False-positive risk: high. Django hits: 46, nearly all `in other words`, plus one
  imperative `simply put a`.
- Tier: `aggressive`.
- Sources: slop-guard `slop_phrase.py`, tbhb/vale-ai-tells `RestatementMarkers.yml`.

### numbered-lead-in

A count announced before a list.

- Examples: `Three key reasons:`, `Here are the five`, `There are three main`.
- Regex: tbhb/vale-ai-tells `CataphoricForecasting.yml` has 13 tokens. A narrow start:
  `\b(?:Two|Three|Four|Five|Six|Seven) (?:key|main|core|critical|essential|fundamental) [a-z]+:`
- False-positive risk: medium. Human docs count list items too.
- Tier: `aggressive`.
- Sources: tbhb/vale-ai-tells `CataphoricForecasting.yml`.

## Word lists that are new

### business-jargon

- Examples: `deep dive`, `game changer`, `paradigm shift`, `move the needle`,
  `secret sauce`, `low-hanging fruit`, `double down`, `lean into`, `circle back`,
  `best-in-class`, `thought leader`, `win-win`.
- Regex (flags `i`):
  `\b(?:game[- ]changer|paradigm shift|move the needle|secret sauce|low-hanging fruit|double down|lean(?:s|ing)? into|circle back|deep dive|best-in-class|thought leader|win-win)\b`
- False-positive risk: low. Django hits: 0.
- Tier: warn.
- Sources: stop-slop "Business Jargon", krishnasunkam/vale-ai-tells `Cliche.yml`, Wikipedia
  (`deep dive`, listed for 2026 from The Economist), Adrian Vega (`Game-changer` 19x).

### claude-figurative

Figurative words that recent Claude models overuse. A regex cannot tell the metaphor from
the literal use, which is why `aggressive.json` already excludes `surface` and `harness`.

- Examples: `load-bearing`, `quietly drops`, `the change lands`, `earns its place`, `seams`,
  `the shape of the problem`.
- Regex (flags `i`):
  `\bload[- ]bearing\b|\bquietly (?:drops?|ignores?|skips?|swallows?|fails?|breaks?|handles?)\b|\bearns? (?:its|their) (?:place|keep)\b`
- False-positive risk: medium. `load-bearing` has a real meaning in civil engineering, and
  `quietly` is fine when it means "without output". Django hits: 1
  (`browsers will quietly ignore the header`).
- Tier: `aggressive`.
- Sources: HN thread and jola.dev post on "How to stop Claude from saying load-bearing",
  tbhb/vale-ai-tells `FigurativeQuiet.yml`, `FigurativeLands.yml`, `FigurativeEarns.yml`,
  tropes.fyi "Quietly and Other Magic Adverbs", Wikipedia (`quietly` in the mid-2026 list).

### invented-concept-label

A coined compound used as if it were an established term.

- Examples: `the supervision paradox`, `the acceleration trap`, `workload creep`,
  `the context tax`.
- Regex (flags `i`): `\bthe [a-z-]+ (?:paradox|trap|tax|creep|cliff|treadmill|divide)\b`
- False-positive risk: medium. Real terms exist (`the birthday paradox`, `scope creep`).
  Django hits: 0.
- Tier: `aggressive`.
- Sources: tropes.fyi "Invented Concept Labels".

## Structural tells a line regex cannot catch well

These are well documented but depend on more than one line, on counts, or on meaning. They
would need a new `kind` in the engine, not a pattern.

- One-line paragraph punch. A one-sentence paragraph that restates the paragraph above. The
  LinkedIn study found one-sentence-per-line formatting in 91% of AI posts. Detecting it
  needs paragraph boundaries and a length check. Sources: tropes.fyi "Short Punchy
  Fragments", humanizer section 2.
- Triads. `X, Y, and Z` is ordinary English. slop-guard flags every match with
  `\w+, \w+, and \w+` and relies on scoring by density. A density threshold per paragraph
  would fit deslopper better than a per-line warning. Sources: Wikipedia "Rule of three",
  tropes.fyi "Tricolon Abuse", krishnasunkam/vale-ai-tells `AbstractTriad.yml`.
- Anaphora. The same sentence opening three or more times in a row. Sources: tropes.fyi
  "Anaphora Abuse", humanizer section 7, tbhb/vale-ai-tells `StackedAnaphora.yml`.
- Listicle in a trench coat. `The first... The second... The third...` across paragraphs.
  Source: tropes.fyi.
- Low sentence-length variance. slop-guard flags a coefficient of variation below 0.3 over
  five or more sentences. Source: slop-guard `rhythm.py`, Graphite.
- False agency. `the decision emerges`, `the data tells us`. A verb list could catch some
  forms, but the false-positive rate in technical prose (`the function returns`) would be
  high. Source: stop-slop "False Agency".
- Fractal summaries and the dead metaphor. Both need the whole document. Source: tropes.fyi.
- False ranges. `From X to Y` where X and Y are not on a scale. A regex finds every
  `from X to Y`, and most are real ranges. Source: tropes.fyi, Wikipedia.

## Widen existing tells

These candidates fit an existing tell's name and message, so they extend its word list or
pattern instead of adding a new tell.

- `not-just-x-but-y`: the pattern only matches `not just`. Add `not only` and `not merely`.
  A draft: `\bnot (?:just|only|merely)\b[^.?!]{0,60}?\b(?:but|it'?s)\b`. Sources: Wikipedia,
  krishnasunkam/vale-ai-tells `NegParallel.yml`, slop-guard
  (`not (just|only) .{1,40}, but (also )?`). Django hits: 3, for example
  `not only per type of object, but also`, so the widening costs a little precision.
- `throat-clearing`: add `It's important to (?:note|remember|understand)`,
  `It bears mentioning`, `Importantly`, `Interestingly`, `Notably`, `Ultimately`,
  `In the realm of`, `In an era where`, `In a world where`, `Imagine a world where`,
  `Picture this`, `Have you ever wondered`, `Since the dawn of`, `As we navigate`. Sources:
  tropes.fyi "It's Worth Noting", tbhb/vale-ai-tells `OpeningCliches.yml`, Graphite
  (`ultimately this` 78x), Wikipedia "Didactic disclaimers".
- `filler-verb`: add `elevates?`, `embark(?:s|ed|ing)?`, `unleash(?:es|ed)?`,
  `bolster(?:s|ed)?`, `orchestrates?`, `transcends?`, `enhances?`. `navigate` is only a tell
  in `navigate the complexities`, so add that phrase, not the verb. Sources: slop-guard
  `slop_word.py`, Wikipedia AI vocabulary, Kobak et al. (`enhancing`).
- `marketing-adjective`: add `groundbreaking`, `holistic`, `multifaceted`, `meticulous`,
  `unparalleled`, `invaluable`, `paramount`, `transformative`, `impactful`, `breathtaking`,
  `stunning`, `revolutionary`, `state-of-the-art`. Django hits for `paramount`: 1
  (`a topic of paramount importance`), so keep `paramount` to warn. Sources: slop-guard
  `slop_word.py`, Graphite hype words, Wikipedia promotional language.
- `inflated-word`: add `realm`, `myriad`, `plethora`, `interconnectedness`, `nuanced`,
  `commendable`, `noteworthy`, `ever-evolving`, `ever-changing`. Sources: slop-guard,
  slop-forensics essay profiles (`interconnectedness`, `multifaceted` near the top for
  gpt-4o-mini), pen2profit.
- `vague-intensifier`: add `genuinely`, `truly`, `incredibly`, `absolutely`, `deeply`,
  `remarkably`, `fundamentally` to `aggressive` (as a new name, since one name cannot sit in
  both presets at the same phase). Graphite reports `incredibly` at 18x for Gemini 3.1 Pro
  and `is genuinely` at 1,021 Opus 5 hits against 4 human. Sources: stop-slop "Adverbs",
  tropes.fyi, Graphite.
- `trailing-participle`: add `emphasizing`, `symbolizing`, `contributing to`, `cultivating`,
  `encompassing`, `enhancing`, `solidifying`, `cementing`, `paving the way`. Sources:
  Wikipedia "Superficial analyses", humanizer section 15.
- `vague-attribution`: add `studies show`, `research suggests`, `it is widely believed`,
  `observers have (?:cited|noted)`, `some argue`, `several (?:sources|publications)`.
  Sources: slop-guard `weasel_phrase.py`, Wikipedia, tropes.fyi.
- `chatbot-phrase`: add `would you like me to`, `if you(?:'d)? (?:want|like), I can`,
  `want me to`, `is there anything else`, `don't hesitate to`, `happy to help`, `shall I`.
  Sources: Wikipedia "Collaborative communication", slop-guard `tone_marker.py`, humanizer
  section 22.
- `sycophancy`: add `you're right to push back`, `that's a fair (?:concern|point)`,
  `good catch`, `I hear you`. Sources: Jodie Cook ("Validation before dismissal"), HN thread
  on Claude stock phrases.
- `fancy-is`: add `functions as`, `operates as`, `holds the distinction`. Sources: Wikipedia
  "Avoidance of basic copulatives", humanizer section 18.
- `puffery`: add `plays? an? (?:crucial|pivotal|vital|key|significant) role`,
  `key turning point`, `focal point`, `enduring legacy`, `rich (?:cultural )?heritage`,
  `nestled`, `in the heart of`, `valuable insights`. slop-forensics found
  `plays crucial role` as the top trigram (248) for gpt-4o-mini essays. Sources: Wikipedia,
  slop-forensics, Kobak et al.
- `generic-conclusion` (aggressive): add `at the end of the day`, `it all comes down to`,
  `in the end,`. Sources: slop-guard `closing_aphorism.py`.
- `cutoff-disclaimer` (aggressive): add the 2024 to 2026 forms,
  `not widely (?:documented|available|disclosed)`,
  `based on (?:the )?available information`,
  `in the (?:provided|available) (?:sources|search results)`,
  `does not by itself establish`. Wikipedia dates the last form to mid-2026 output. Source:
  Wikipedia "Hedging disclaimers".
- `emoji` or a new `unicode-arrow` tell: tropes.fyi reports `→` in prose as a Claude habit.
  UI paths (`Settings → General`) use it honestly, so it belongs in `aggressive`.

## Sources

Primary rule files and code:

- tbhb/vale-ai-tells, `styles/ai-tells/*.yml`: https://github.com/tbhb/vale-ai-tells
- krishnasunkam/vale-ai-tells, `AiTells/*.yml`:
  https://github.com/krishnasunkam/vale-ai-tells
- slop-guard by Eric Tramel, `src/slop_guard/rules/`:
  https://github.com/eric-tramel/slop-guard and the write-up at
  https://eric-tramel.github.io/blog/2026-02-18-slop-guard
- stop-slop by Hardik Pandya, `references/phrases.md` and `references/structures.md`:
  https://github.com/hardikpandya/stop-slop
- humanizer by blader, `SKILL.md` (v3.1.0): https://github.com/blader/humanizer
- tropes.md by Ossama: https://tropes.fyi and
  https://gist.github.com/ossa-ma/f3baa9d25154c33095e22272c631f5a1
- Sam Paech, antislop-sampler `slop_regexes.txt` and phrase lists:
  https://github.com/sam-paech/antislop-sampler (mostly fiction slop, with little overlap
  for technical docs)
- Sam Paech, slop-forensics essay profiles: https://github.com/sam-paech/slop-forensics

Articles and studies:

- Wikipedia, "Signs of AI writing" (WikiProject AI Cleanup), read from the wikitext source:
  https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing
- Graphite, "AI Tells" (Druck, Paredes, Smith, 2026-09-16):
  https://graphite.io/five-percent/research/ai-tells
- Kobak, Gonzalez-Marquez, Horvat, Lause, "Delving into LLM-assisted writing in biomedical
  publications through excess vocabulary": https://arxiv.org/abs/2406.07016
- Adrian Vega, "I Analyzed 500 AI-Generated LinkedIn Posts" (self-reported counts, method
  not disclosed):
  https://dev.to/adrianvegaresearch/i-analyzed-500-ai-generated-linkedin-posts-heres-what-they-all-have-in-common-2h36
- Jodie Cook, ban list: https://www.jodiecook.com/ban-list/
- Ruben Hassid, "Ban these ChatGPT words": https://ruben.substack.com/p/delve <!-- deslop-lint-disable-line -->
- pen2profit, "Writing that Smacks of Bot":
  https://pen2profit.substack.com/p/writing-that-smacks-of-bot-is-that
- jola.dev, "How to stop Claude from saying load-bearing", and its HN thread:
  https://news.ycombinator.com/item?id=48905248
- "The not-X-but-Y machine": https://buddha.bearblog.dev/the-not-x-but-y-machine/
- The Economist analysis of chatbot prose (2026) was read only through secondary coverage,
  for example https://daringfireball.net/linked/2026/08/11/economist-ai-writing

Human baseline corpus: Django 3.2 docs, https://github.com/django/django/tree/3.2/docs
