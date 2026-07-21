"""Render the README's tell table from the recommended preset.

The table between the markers below is generated, and tests/test_readme.py
fails when it drifts from the preset. After changing a tell, run:

    python scripts/readme_tells.py

Each row carries an example that the tests assert really fires the tell, so a
new tell needs an entry in EXAMPLES here before the table will render.
"""

import os
import re

from deslopper.config import resolve

BEGIN = "<!-- tell-table:begin -->"
END = "<!-- tell-table:end -->"
README = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "README.md")

TIER_EMOJI = {"error": "❌", "warn": "⚠️"}

# One slop snippet per tell, shown in the table and pinned by
# test_every_example_fires_exactly_its_tell.
EXAMPLES = {
    "em-dash": "A quick fix — just restart.",
    "section-sign": "See § 4.2 for details.",
    "middle-dot": "fast · simple · tested",
    "bold-bullet-lead": "- **Blazing speed** builds finish in seconds",
    "id-label-lead": "- FR-1 The app shall sync.",
    "semicolon": "It compiles; it ships.",
    "not-just-x-but-y": "not just fast but correct",
    "filler-verb": "This leverages the cache.",
    "marketing-adjective": "a seamless, robust workflow",
    "throat-clearing": "It's worth noting that tests pass.",
    "vague-intensifier": "significantly faster",
    "emoji": "Done ✅",
}


def _rows():
    # One row per name. The three entity-capable tells appear twice in the
    # preset (pre- and post-entity); the post-entity message is the prose-facing
    # one, and the preset lists it second, so the later duplicate wins.
    rows = {}
    for t in resolve({}).tells:
        if t.name not in EXAMPLES:
            raise SystemExit(f"no EXAMPLES entry for tell {t.name!r}")
        rows[t.name] = (TIER_EMOJI[t.tier], t.message)
    return rows


def render_block() -> str:
    lines = [
        BEGIN,
        "<!-- deslop-lint-disable -->",
        "",
        "❌ error, fails the run. ⚠️ warn, passes unless `--strict`.",
        "",
        "| Tell | Tier | Example | Message |",
        "| --- | --- | --- | --- |",
    ]
    for name, (tier, message) in _rows().items():
        example = EXAMPLES[name].replace("|", "\\|")
        message = message.replace("|", "\\|")
        lines.append(f"| `{name}` | {tier} | `{example}` | {message} |")
    lines += ["", "<!-- deslop-lint-enable -->", END]
    return "\n".join(lines)


def main() -> int:
    with open(README, encoding="utf-8") as fh:
        text = fh.read()
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        raise SystemExit(f"no {BEGIN} ... {END} block in README.md")
    with open(README, "w", encoding="utf-8") as fh:
        fh.write(pattern.sub(lambda _: render_block(), text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
