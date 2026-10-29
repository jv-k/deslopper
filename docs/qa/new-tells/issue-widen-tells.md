Blocked by: #60

## What to build

Widen fifteen existing tells with words and patterns that other slop detectors list and deslopper misses. The additions come from a survey of those tools and articles. Each item names its sources.

This is blocked by the new-tells issue because both change the same golden files, eval fixtures and README table. Start from `main` after that one merges.

Most items extend a tell in `recommended.json`. Three items go to `aggressive.json`:

- `generic-conclusion` and `cutoff-disclaimer` already exist there. Extend them.
- The extra intensifiers (`genuinely`, `truly` and so on) go in a new aggressive tell. Name it `strong-intensifier`, because a name cannot sit in both presets at the same phase.
- The arrow `→` goes in a new aggressive tell named `unicode-arrow`. Do not add it to `emoji`, since UI paths such as `Settings → General` use it honestly.

Write the failing fixture cases first. Then follow CONTRIBUTING.md: regenerate the `comprehensive.*.golden` files, the eval fixtures and the README tells table. A new aggressive tell needs no eval seed unless the eval suite checks the aggressive preset too.

For `not-just-x-but-y`, the survey found 3 hits in the Django docs, such as `not only per type of object, but also`. Accept that cost. It stays at warn.

If an addition fires on the repo's own Markdown, decide per hit. Rewrite slop. Drop the word from the list if the hit is honest prose, and note it in the PR.

## Acceptance criteria

- [ ] Every addition listed below fires its tell in a fixture case.
- [ ] `strong-intensifier` and `unicode-arrow` exist in `aggressive.json` at tier `warn`.
- [ ] Golden files, eval fixtures and the README tells table are regenerated, and the PR says the golden change is intended.
- [ ] `pytest -q` passes and `deslopper lint` passes on the repo.

## The additions

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
