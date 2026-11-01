"""Render the README's tell tables and tell counts from the shipped presets.

The tables between the marker pairs below, and the tell counts in the highlights
line, are generated, and tests/test_readme.py fails when any of them drifts from
its preset. After changing a tell, run:

    python scripts/readme_tells.py

Each row carries an example that the tests assert really fires the tell, so a
new tell needs an entry in EXAMPLES (or AGGRESSIVE_EXAMPLES) here before the
table will render.
"""

import os
import re

from deslopper.config import resolve

BEGIN = "<!-- tell-table:begin -->"
END = "<!-- tell-table:end -->"
AGGRESSIVE_BEGIN = "<!-- aggressive-table:begin -->"
AGGRESSIVE_END = "<!-- aggressive-table:end -->"
# The highlights line. The counts are the number of tell names in each preset.
COUNTS_TEMPLATE = (
    "A deterministic lint for {recommended} tells, "
    "with an opt-in `aggressive` preset for {aggressive} more."
)
COUNTS_PATTERN = re.compile(
    re.escape(COUNTS_TEMPLATE)
    .replace(r"\{recommended\}", r"\d+")
    .replace(r"\{aggressive\}", r"\d+")
)
README = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "README.md")

TIER_EMOJI = {"error": "❌", "warn": "⚠️"}

# One slop snippet per tell, shown in the table and pinned by
# test_every_example_fires_exactly_its_tell.
EXAMPLES = {
    "em-dash": "A quick fix — just restart.",
    "section-sign": "See § 4.2 for details.",
    "middle-dot": "fast · simple · tested",
    "curly-quote": "It’s “done” now.",
    "bold-bullet-lead": "- **Blazing speed** builds finish in seconds",
    "id-label-lead": "- FR-1 The app shall sync.",
    "semicolon": "It compiles; it ships.",
    "not-just-x-but-y": "not just fast but correct",
    "filler-verb": "This leverages the cache.",
    "marketing-adjective": "a seamless, robust workflow",
    "throat-clearing": "It's worth noting that tests pass.",
    "vague-intensifier": "significantly faster",
    "emoji": "Done ✅",
    "chatbot-phrase": "I hope this helps!",
    "sycophancy": "Great question!",
    "fancy-is": "The CLI boasts three modes.",
    "puffery": "A testament to good design.",
    "vague-attribution": "Experts believe it scales.",
    "inflated-word": "A crucial, intricate detail.",
    "trailing-participle": "It retries, ensuring delivery.",
    "false-exclusivity": "Nobody talks about the cost.",
    "hidden-truth": "The uncomfortable truth: tests rot.",
    "real-problem-reframe": "The real problem isn't speed.",
    "false-suspense": "Here's the thing: it caches.",
    "rhetorical-self-answer": "The catch? It only runs on Linux.",
    "emphasis-crutch": "It never drops a job. Let that sink in.",
    "staged-candor": "Honestly? It depends.",
    "mic-drop": "That's the whole point.",
    "negation-pivot": "It's not a bug. It's a feature.",
    "importance-flag": "This matters because retries add up.",
    "signposting": "In conclusion, the cache works.",
    "urgency-inflation": "Fast builds have never been more critical.",
    "stacked-hedge": "The job could potentially fail.",
    "tradeoff-dodge": "Fast without sacrificing safety.",
    "pithy-fragment": "Dense, not cramped.",
    "narrative-pivot": "Then something shifted.",
    "negative-listing": "No config, no flags, just one binary.",
    "business-jargon": "This will move the needle.",
}

# The opt-in aggressive layer, pinned by test_every_aggressive_example_fires_its_tell.
AGGRESSIVE_EXAMPLES = {
    "abstract-metaphor": "Our north star is the flywheel.",
    "cutoff-disclaimer": "Specific details are limited.",
    "formulaic-challenge": "Despite challenges, it continues to thrive.",
    "generic-conclusion": "The future looks bright.",
    "boldface-overuse": "**Fast**, **safe**, **simple**.",
    "strong-intensifier": "It is genuinely fast.",
    "unicode-arrow": "Build → test → ship.",
    "missing-piece": "This is the missing piece.",
    "contrarian-hook": "Most teams get this backwards.",
    "overreach": "There's no denying it scales.",
    "invented-concept-label": "Call it the context tax.",
    "tutorial-signposting": "Let's dive in.",
    "contrast-adverb": "It is not simply a cache.",
    "strawman-tail": "It keeps one copy, not one per caller.",
    "restatement-marker": "In other words, it caches.",
    "numbered-lead-in": "Three key reasons:",
    "claude-figurative": "This check is load-bearing.",
}


def _recommended_tells():
    return resolve({}).tells


def _aggressive_tells():
    return resolve({"extends": ["deslopper:aggressive"]}).tells


def _rows(tells, examples):
    # One row per name. The entity-capable tells appear twice in the preset
    # (pre- and post-entity); the post-entity message is the prose-facing one,
    # and the preset lists it second, so the later duplicate wins.
    rows = {}
    for t in tells:
        if t.name not in examples:
            raise SystemExit(f"no example entry for tell {t.name!r}")
        rows[t.name] = (TIER_EMOJI[t.tier], t.message)
    return rows


def _render(begin, end, legend, tells, examples) -> str:
    lines = [
        begin,
        "<!-- deslop-lint-disable -->",
        "",
        legend,
        "",
        "| Tell | Tier | Example | Message |",
        "| --- | --- | --- | --- |",
    ]
    for name, (tier, message) in _rows(tells, examples).items():
        example = examples[name].replace("|", "\\|")
        message = message.replace("|", "\\|")
        lines.append(f"| `{name}` | {tier} | `{example}` | {message} |")
    lines += ["", "<!-- deslop-lint-enable -->", end]
    return "\n".join(lines)


def render_block() -> str:
    return _render(
        BEGIN,
        END,
        "❌ error, fails the run. ⚠️ warn, passes unless `--strict`.",
        _recommended_tells(),
        EXAMPLES,
    )


def render_aggressive_block() -> str:
    return _render(
        AGGRESSIVE_BEGIN,
        AGGRESSIVE_END,
        "⚠️ warn throughout: the layer trades precision for reach, and you triage.",
        _aggressive_tells(),
        AGGRESSIVE_EXAMPLES,
    )


def render_counts() -> str:
    recommended = {t.name for t in _recommended_tells()}
    aggressive = {t.name for t in _aggressive_tells()}
    return COUNTS_TEMPLATE.format(recommended=len(recommended), aggressive=len(aggressive))


def _substitute(text, pattern, block, what) -> str:
    if not pattern.search(text):
        raise SystemExit(f"no {what} in README.md")
    return pattern.sub(lambda _: block, text)


def _marker_pattern(begin, end):
    return re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)


def main() -> int:
    with open(README, encoding="utf-8") as fh:
        text = fh.read()
    for begin, end, block in (
        (BEGIN, END, render_block()),
        (AGGRESSIVE_BEGIN, AGGRESSIVE_END, render_aggressive_block()),
    ):
        text = _substitute(text, _marker_pattern(begin, end), block, f"{begin} ... {end} block")
    text = _substitute(text, COUNTS_PATTERN, render_counts(), "tell-count line")
    with open(README, "w", encoding="utf-8") as fh:
        fh.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
