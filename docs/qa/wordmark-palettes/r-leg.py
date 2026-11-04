"""Draws the R alone with its leg moved in by several amounts, in the Monokai gradient,
on GitHub's dark page. One stroke is 14 px wide; the foot moves with the leg.

    .venv/bin/python docs/qa/wordmark-palettes/r-leg.py | rsvg-convert -o r-leg.png
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import wordmark  # noqa: E402

wordmark.ROWS = ["┏━┓", "┣━┫", "╹ ┗"]
S = wordmark.STROKE
PUSHES = [("0", 0), ("3 px (now)", 3), ("1/2 stroke", S / 2), ("1 stroke", S),
          ("1.5 strokes", 1.5 * S), ("2 strokes", 2 * S), ("2.5 strokes", 2.5 * S),
          ("3 strokes", 3 * S)]

COLS, TILE_W, TILE_H, PAD = 4, 230, 280, 16
left, top = wordmark.LEFT - wordmark.W / 2, wordmark.TOP - wordmark.H / 2
GW, GH = 3 * wordmark.W, 3 * wordmark.H
rows = (len(PUSHES) + COLS - 1) // COLS
sw, sh = COLS * (TILE_W + PAD) + PAD, rows * (TILE_H + PAD) + PAD
out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{sw}" height="{sh}">',
       f'<rect width="{sw}" height="{sh}" fill="#f6f8fa"/>',
       '<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x1="%g" y1="%g" '
       'x2="%g" y2="%g"><stop offset="0" stop-color="#a9dc76"/>'
       '<stop offset="1" stop-color="#78dce8"/></linearGradient></defs>'
       % (left, top, left + GW, top + GH)]
for i, (name, push) in enumerate(PUSHES):
    wordmark.LEG_NUDGE = -push
    x, y = PAD + (i % COLS) * (TILE_W + PAD), PAD + (i // COLS) * (TILE_H + PAD)
    scale = min((TILE_W - 60) / GW, (TILE_H - 80) / GH)
    out += [f'<rect x="{x}" y="{y}" width="{TILE_W}" height="{TILE_H}" rx="10" fill="#0d1117"/>',
            f'<text x="{x + 12}" y="{y + 28}" font-family="Helvetica" font-size="18" '
            f'font-weight="bold" fill="#8b949e">{i + 1}  {name}</text>',
            f'<g transform="translate({x + 30},{y + 55}) scale({scale}) translate({-left},{-top})">'
            f'<g fill="url(#g)" shape-rendering="crispEdges">{"".join(wordmark.rects())}</g></g>']
out.append("</svg>")
sys.stdout.write("\n".join(out) + "\n")
