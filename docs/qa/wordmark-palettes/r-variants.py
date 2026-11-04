"""Draws the wordmark with each candidate R, on GitHub's dark page.

    .venv/bin/python docs/qa/wordmark-palettes/r-variants.py | rsvg-convert -o r-variants.png
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import wordmark  # noqa: E402

BASE = [row[:-1] for row in wordmark.WORDMARK]
VARIANTS = {
    "R1  now": ("┏━┓", "┣┳┛", "╹┗╸"),
    "R7  bowl as A, short foot to the right": ("┏━┓", "┣━┫", "╹ ┗"),
    "R8  4 wide: bowl as A, foot kicks past it": ("┏━┓ ", "┣━┫ ", "╹ ┗╸"),
    "R9  4 wide: leg steps down and out past the bowl": ("┏━┓ ", "┣┳┛ ", "╹┗━╸"),
    "R10 4 wide: wide bowl, leg near its right side": ("┏━━┓", "┣━┳┛", "╹ ╹ "),
    "R11 4 wide: wide bowl, leg steps out to the right": ("┏━━┓", "┣━┳┛", "╹ ┗╸"),
    "R12 4 wide: wide bowl, leg under its right edge": ("┏━━┓", "┣━━┫", "╹  ┗"),
}
STOPS = ["#ffd866", "#a9dc76", "#78dce8"]
W, H, PAD, LABEL, SCALE = 1144, 237, 24, 34, 0.5
cw, ch = W * SCALE, H * SCALE
sw, rh = int(cw + 2 * PAD), LABEL + ch + PAD
sh = int(PAD + len(VARIANTS) * rh)
out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{sw}" height="{sh}">',
       f'<rect width="{sw}" height="{sh}" fill="#f6f8fa"/>']
for i, (name, r) in enumerate(VARIANTS.items()):
    wordmark.ROWS = ["".join(row) + r[y] for y, row in enumerate(BASE)]
    y = PAD + i * rh
    body = wordmark.svg(STOPS).replace('id="g"', f'id="g{i}"').replace("url(#g)", f"url(#g{i})")
    body = body.split(">", 1)[1].rsplit("</svg>", 1)[0]
    out += [f'<text x="{PAD}" y="{y + 22}" font-family="Helvetica" font-size="20" '
            f'font-weight="bold" fill="#24292f">{name}</text>',
            f'<rect x="{PAD}" y="{y + LABEL}" width="{cw}" height="{ch}" rx="8" fill="#0d1117"/>',
            f'<svg x="{PAD}" y="{y + LABEL}" width="{cw}" height="{ch}" viewBox="0 0 {W} {H}">{body}</svg>']
out.append("</svg>")
sys.stdout.write("\n".join(out) + "\n")
