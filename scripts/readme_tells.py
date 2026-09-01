"""Render the README's tell tables from the shipped presets.

The tables between the marker pairs below are generated, and tests/test_readme.py
fails when either drifts from its preset. After changing a tell, run:

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
}

# The opt-in aggressive layer, pinned by test_every_aggressive_example_fires_its_tell.
AGGRESSIVE_EXAMPLES = {
    "abstract-metaphor": "Our north star is the flywheel.",
    "cutoff-disclaimer": "Specific details are limited.",
    "formulaic-challenge": "Despite challenges, it continues to thrive.",
    "generic-conclusion": "The future looks bright.",
    "boldface-overuse": "**Fast**, **safe**, **simple**.",
}


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
        resolve({}).tells,
        EXAMPLES,
    )


def render_aggressive_block() -> str:
    return _render(
        AGGRESSIVE_BEGIN,
        AGGRESSIVE_END,
        "⚠️ warn throughout: the layer trades precision for reach, and you triage.",
        resolve({"extends": ["deslopper:aggressive"]}).tells,
        AGGRESSIVE_EXAMPLES,
    )


def _substitute(text, begin, end, block) -> str:
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    if not pattern.search(text):
        raise SystemExit(f"no {begin} ... {end} block in README.md")
    return pattern.sub(lambda _: block, text)


def main() -> int:
    with open(README, encoding="utf-8") as fh:
        text = fh.read()
    text = _substitute(text, BEGIN, END, render_block())
    text = _substitute(text, AGGRESSIVE_BEGIN, AGGRESSIVE_END, render_aggressive_block())
    with open(README, "w", encoding="utf-8") as fh:
        fh.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
