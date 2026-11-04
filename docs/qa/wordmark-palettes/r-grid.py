"""Draws 20 candidate R glyphs on their own, in the Monokai gradient, on GitHub's dark page.

    .venv/bin/python docs/qa/wordmark-palettes/r-grid.py | rsvg-convert -o r-grid.png
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import wordmark  # noqa: E402

RS = [
    ("┏━┓", "┣┳┛", "╹┗╸"),   # 1 now
    ("┏━┓", "┣┳┛", "╹╹ "),   # 2
    ("┏━┓", "┣┳┛", "╹┗━"),   # 3
    ("┏━┓", "┣━┫", "╹ ╹"),   # 4
    ("┏━┓", "┣━┫", "╹ ┗"),   # 5
    ("┏━┓", "┣━┛", "╹ ╹"),   # 6
    ("┳━┓", "┣━┫", "┻ ┗"),   # 7
    ("┳━┓", "┣┳┛", "┻┗╸"),   # 8
    ("┳━┓", "┣┳┛", "┻╹ "),   # 9
    ("┳━┓", "┣━┫", "╹ ┗"),   # 10
    ("┏━┓ ", "┣┳┛ ", "╹┗━╸"),  # 11
    ("┏━┓ ", "┣━┫ ", "╹ ┗╸"),  # 12
    ("┏━┓ ", "┣━┻┓", "╹  ╹"),  # 13
    ("┏━┓ ", "┣━┻┓", "╹  ┗"),  # 14
    ("┏━━┓", "┣━┳┛", "╹ ╹ "),  # 15
    ("┏━━┓", "┣━┳┛", "╹ ┗╸"),  # 16
    ("┏━━┓", "┣━━┫", "╹  ╹"),  # 17
    ("┏━━┓", "┣━━┫", "╹  ┗"),  # 18
    ("┏━━┓", "┣┳━┛", "╹┗━╸"),  # 19
    ("┳━━┓", "┣━┳┛", "┻ ┗╸"),  # 20
]

COLS, TILE_W, TILE_H, PAD = 5, 230, 260, 16
GLYPH_W, GLYPH_H = 4 * wordmark.W, 3 * wordmark.H
rows = (len(RS) + COLS - 1) // COLS
sw, sh = COLS * (TILE_W + PAD) + PAD, rows * (TILE_H + PAD) + PAD
out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{sw}" height="{sh}">',
       f'<rect width="{sw}" height="{sh}" fill="#f6f8fa"/>',
       # One gradient across the whole 4-cell box, in the glyph's own coordinates.
       '<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x1="%g" y1="%g" '
       'x2="%g" y2="%g"><stop offset="0" stop-color="#ffd866"/>'
       '<stop offset="0.5" stop-color="#a9dc76"/><stop offset="1" stop-color="#78dce8"/>'
       '</linearGradient></defs>' % (wordmark.LEFT - wordmark.W / 2, wordmark.TOP - wordmark.H / 2,
                                     wordmark.LEFT - wordmark.W / 2 + GLYPH_W,
                                     wordmark.TOP - wordmark.H / 2 + GLYPH_H)]
for i, r in enumerate(RS):
    x, y = PAD + (i % COLS) * (TILE_W + PAD), PAD + (i // COLS) * (TILE_H + PAD)
    wordmark.ROWS = list(r)
    # Each glyph sits in a 4-cell box from the first cell's left edge, so widths compare.
    left, top = wordmark.LEFT - wordmark.W / 2, wordmark.TOP - wordmark.H / 2
    scale = (TILE_W - 50) / GLYPH_W
    body = "\n".join(wordmark.rects())
    out += [f'<rect x="{x}" y="{y}" width="{TILE_W}" height="{TILE_H}" rx="10" fill="#0d1117"/>',
            f'<text x="{x + 12}" y="{y + 28}" font-family="Helvetica" font-size="20" '
            f'font-weight="bold" fill="#8b949e">{i + 1}</text>',
            f'<g transform="translate({x + 25},{y + 50}) scale({scale}) translate({-left},{-top})">'
            f'<g fill="url(#g)" shape-rendering="crispEdges">{body}</g></g>']
out.append("</svg>")
sys.stdout.write("\n".join(out) + "\n")
