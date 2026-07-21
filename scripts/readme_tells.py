"""Render the README's tell table from the recommended preset.

The table between the markers below is generated, and tests/test_readme.py
fails when it drifts from the preset. After changing a tell, run:

    python scripts/readme_tells.py
"""

import os
import re

from deslopper.config import resolve

BEGIN = "<!-- tell-table:begin -->"
END = "<!-- tell-table:end -->"
README = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "README.md")


def render_block() -> str:
    # resolve({}) is the linter's own defaults path, so the table shows the
    # recommended preset as shipped, not this repo's config.
    lines = [
        BEGIN,
        "<!-- deslop-lint-disable -->",
        "",
        "| Tell | Tier | Phase | Message |",
        "| --- | --- | --- | --- |",
    ]
    for t in resolve({}).tells:
        message = t.message.replace("|", "\\|")
        lines.append(f"| `{t.name}` | {t.tier} | {t.phase} | {message} |")
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
