"""Draws the README's wordmark as an SVG on stdout: the CLI's rows from help.py, each
box-drawing cell as thick strokes, under the CLI's diagonal gradient.
scripts/screenshots.sh turns it into img/wordmark-dark.png and img/wordmark-light.png.
Pass `light` for the darker stops that read on white.

    python3 scripts/wordmark.py [dark | light] > wordmark.svg
"""

import sys

from deslopper.help import WORDMARK
from deslopper.ui import GRADIENT_SHIFT, GRADIENT_STOPS

# The picture draws its own R: the leg under the bowl's right side, moved one stroke in
# by LEG_NUDGE. A terminal moves a stroke only by whole cells, so the CLI's R has its
# leg one cell in instead.
PICTURE_R = ("┏━┓", "┣━┫", "╹ ┗")
ROWS = ["".join(row[:-1]) + r for row, r in zip(WORDMARK, PICTURE_R)]

# The CLI's stops for a dark page, and darker ones for a light page.
STOPS = {
    "dark": ["#%02x%02x%02x" % stop for stop in GRADIENT_STOPS],
    "light": ["#b88a00", "#4f8f1f", "#13849c"],
}

# Each glyph as the arms it draws from the cell's centre.
ARMS = {
    "┏": "rd", "┓": "ld", "┗": "ur", "┛": "ul", "━": "lr", "┃": "ud",
    "┣": "udr", "┫": "udl", "┳": "lrd", "┻": "lru",
    "╸": "l", "╺": "r", "╹": "u", "╻": "d",
}

W, H = 38.5, 63.5  # a cell's width and height
STROKE = 14
LEFT, TOP = 52, 55  # the first cell's centre
HALF = STROKE / 2

# The R's leg, from its middle bar down to its foot, sits one stroke left of the
# bowl's right side.
LEG_NUDGE = -STROKE


def nudge(x, y, arm):
    """How far to move the stroke for `arm` of the cell at column x, row y."""
    leg = x == len(ROWS[0]) - 1 and ((y == 1 and arm == "d") or y == 2)
    return LEG_NUDGE if leg and ROWS[1].endswith("┫") else 0


def rects():
    out = []
    for y, row in enumerate(ROWS):
        for x, cell in enumerate(row):
            cx, cy = LEFT + x * W, TOP + y * H
            for arm in ARMS.get(cell, ""):
                r = {
                    "l": (cx - W / 2, cy - HALF, W / 2 + HALF, STROKE),
                    "r": (cx - HALF, cy - HALF, W / 2 + HALF, STROKE),
                    "u": (cx - HALF, cy - H / 2, STROKE, H / 2 + HALF),
                    "d": (cx - HALF, cy - HALF, STROKE, H / 2 + HALF),
                }[arm]
                r = (r[0] + nudge(x, y, arm),) + r[1:]
                out.append('<rect x="%g" y="%g" width="%g" height="%g"/>' % r)
    return out


def svg(stops):
    # The gradient runs from the first cell's centre, across the direction in which a
    # cell's place in it, (x + SHIFT * y) / span, grows.
    span = len(ROWS[0]) - 1 + GRADIENT_SHIFT * (len(ROWS) - 1)
    gx, gy = 1 / W, GRADIENT_SHIFT / H
    s = span / (gx * gx + gy * gy)
    width = round(2 * LEFT + (len(ROWS[0]) - 1) * W)
    height = round(2 * TOP + (len(ROWS) - 1) * H)
    stop_tags = "\n".join('<stop offset="%g" stop-color="%s"/>' % (i / (len(stops) - 1), c)
                          for i, c in enumerate(stops))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        f'<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x1="{LEFT}" '
        f'y1="{TOP}" x2="{LEFT + s * gx:g}" y2="{TOP + s * gy:g}">\n{stop_tags}\n'
        "</linearGradient></defs>\n"
        '<g fill="url(#g)" shape-rendering="crispEdges">\n'
        + "\n".join(rects())
        + "\n</g>\n</svg>\n"
    )


if __name__ == "__main__":
    sys.stdout.write(svg(STOPS["light" if sys.argv[1:] == ["light"] else "dark"]))
