"""Draws a contact sheet of wordmark palettes, each on GitHub's dark page and on white.

    .venv/bin/python docs/qa/wordmark-palettes/sheet.py | rsvg-convert -o sheet.png
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from wordmark import svg  # noqa: E402

# name: (stops for a dark page, stops for a light page)
PALETTES = {
    "A  claude-gauge: coral, pink, violet": (
        ["#f2774a", "#e04592", "#8b5cf6"], ["#d9572b", "#c42a78", "#6b3fd9"]),
    "B  Monokai: yellow, green, cyan": (
        ["#ffd866", "#a9dc76", "#78dce8"], ["#b88a00", "#4f8f1f", "#13849c"]),
    "C  Fresh: mint, cyan, blue": (
        ["#34d399", "#22d3ee", "#60a5fa"], ["#059669", "#0891b2", "#2563eb"]),
    "D  Lime, teal, indigo": (
        ["#a3e635", "#2dd4bf", "#818cf8"], ["#5f9a0b", "#0d9488", "#4f46e5"]),
    "E  Lavender, periwinkle, sky (the CLI's own accents)": (
        ["#ab9df2", "#87afff", "#78dce8"], ["#6d5bd0", "#3b6fd6", "#13849c"]),
    "F  Sunrise: gold, orange, rose": (
        ["#fde047", "#fb923c", "#f43f5e"], ["#b98500", "#e0560b", "#d4163f"]),
}

W, H, PAD, LABEL = 1105, 237, 24, 34
SCALE = 0.5
cell_w, cell_h = W * SCALE, H * SCALE
sheet_w = int(2 * cell_w + 3 * PAD)
row_h = LABEL + cell_h + PAD
sheet_h = int(PAD + len(PALETTES) * row_h)

parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{sheet_w}" height="{sheet_h}">',
         f'<rect width="{sheet_w}" height="{sheet_h}" fill="#f6f8fa"/>']
for i, (name, (dark, light)) in enumerate(PALETTES.items()):
    y = PAD + i * row_h
    parts.append(f'<text x="{PAD}" y="{y + 22}" font-family="Helvetica" font-size="20" '
                 f'font-weight="bold" fill="#24292f">{name}</text>')
    for j, (stops, bg) in enumerate(((dark, "#0d1117"), (light, "#ffffff"))):
        x = PAD + j * (cell_w + PAD)
        body = svg(stops).replace('id="g"', f'id="g{i}{j}"').replace("url(#g)", f"url(#g{i}{j})")
        body = body.split(">", 1)[1].rsplit("</svg>", 1)[0]
        parts.append(f'<rect x="{x}" y="{y + LABEL}" width="{cell_w}" height="{cell_h}" '
                     f'rx="8" fill="{bg}" stroke="#d0d7de"/>')
        parts.append(f'<svg x="{x}" y="{y + LABEL}" width="{cell_w}" height="{cell_h}" '
                     f'viewBox="0 0 {W} {H}">{body}</svg>')
parts.append("</svg>")
sys.stdout.write("\n".join(parts) + "\n")
