## What to build

Add ten new tells to `src/deslopper/presets/recommended.json`, all at tier `warn` with flags `i`. They come from a survey of other slop detectors and articles. Four of them cover the "nobody noticed the gap" family: prose that claims everyone else missed something (`false-exclusivity`, `hidden-truth`, `real-problem-reframe`), plus the staging moves that usually go with it.

Each draft regex below was run over the Django 3.2 docs (141,541 lines written before chatbots) as a stand-in for human technical prose. Every one had 0 hits there.

Follow "Add a tell to the recommended set" in CONTRIBUTING.md for each tell:

1. Write the failing test first: a case in `tests/fixtures/comprehensive.md`.
2. Add the JSON object. Escape backslashes for JSON. Write a short `message` in the style of the existing ones (what is wrong, then what to do).
3. Regenerate the `comprehensive.*.golden` files.
4. Seed the tell into the eval fixtures in `src/deslopper/data/eval/`.
5. Add an example to `EXAMPLES` in `scripts/readme_tells.py` and regenerate the README table.

Keep `negation-pivot` as its own tell. Do not merge it into `not-just-x-but-y`.

If a new tell fires on the repo's own Markdown, decide per hit. Rewrite the prose if it is slop. Narrow the regex if the hit is honest prose, and note the change in the PR.

## Acceptance criteria

- [ ] The ten tells below exist in `recommended.json` at tier `warn`.
- [ ] Each example phrase listed under a tell fires that tell. Each negative case named in the false-positive notes does not fire it.
- [ ] Golden files, eval fixtures and the README tells table are regenerated, and the PR says the golden change is intended.
- [ ] `pytest -q` passes and `deslopper lint` passes on the repo.

## The tells

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
- Tier: warn.
- Sources: stop-slop `structures.md` ("[X] isn't the problem. [Y] is.", "The answer isn't X.
  It's Y.", "The question isn't X. It's Y."), Ruben Hassid ("The real work isn't X. It's
  Y."), slop-guard `closing_aphorism.py` (`^the (real|true|actual|biggest|...)`), pen2profit
  ("It was never about the thing" is cited in search results but was not on the page when
  fetched).

### false-suspense

A phrase that announces a reveal before an ordinary point. The current `throat-clearing`
tell does not include any `here's` form.

- Examples: `Here's the thing:`, `Here's the kicker.`, `Here's where it gets interesting.`,
  `Here's why this matters.`, `Here's what I learned.`, `The kicker`.
- Regex (flags `i`):
  `\bhere'?s (?:the (?:thing|kicker|catch|deal|twist|truth|reality|secret|rub|part)|where (?:it|things) gets? (?:interesting|tricky|weird|good)|what (?:most|nobody|no one|everyone|few|I (?:learned|found|mean|noticed)|you need to know|matters)|why (?:this|that|it) matters)\b|\bthe kicker\b`
- False-positive risk: low. `Here's how` and `Here's the output` stay out. Django has 17
  lines with `here's the`, and none match. `Here's the catch` is the riskiest branch.
- Tier: warn. This is the top non-gap candidate: the LinkedIn study found `Here's the thing`
  in 170 of 500 posts.
- Sources: tropes.fyi "Here's the Kicker", stop-slop `phrases.md`, slop-guard
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
