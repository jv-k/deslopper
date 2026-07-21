"""The protected-content digest the eval's preservation judge compares.

A digest is what a rewrite pass must not touch: fenced code and front matter
verbatim, the heading outline, table rows with cells normalised, and link
destinations in order. Extracted before and after the rewrite and compared
exactly.
"""

import re
from dataclasses import dataclass
from typing import List, Optional

from .engine import FRONT_CLOSE, FRONT_OPEN, FenceTracker

HEADING = re.compile(r"^ {0,3}#{1,6}\s")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
SEPARATOR_CELL = re.compile(r"^:?-+:?$")
LINK_DEST = re.compile(r"\]\(\s*([^)\s]+)[^)]*\)")


@dataclass(frozen=True)
class Digest:
    front_matter: Optional[str]
    headings: List[str]
    fences: List[str]
    table_rows: List[List[str]]
    links: List[str]


# Field name to the label a preservation report prints, in report order.
COMPONENTS = [
    ("front_matter", "front matter"),
    ("headings", "headings"),
    ("fences", "fenced code"),
    ("table_rows", "table rows"),
    ("links", "link destinations"),
]


def _cells(line: str):
    inner = line.strip().strip("|")
    return [c.strip() for c in inner.split("|")]


def _is_separator(cells) -> bool:
    return all(SEPARATOR_CELL.match(c) for c in cells)


def digest_text(text: str) -> Digest:
    front = None
    headings, fences, rows, links = [], [], [], []

    lines = text.splitlines()
    i = 0
    if lines and FRONT_OPEN.match(lines[0]):
        j = 1
        while j < len(lines) and not FRONT_CLOSE.match(lines[j]):
            j += 1
        front = "\n".join(lines[: j + 1])
        i = j + 1

    tracker = FenceTracker()
    block = []
    for line in lines[i:]:
        kind = tracker.feed(line)
        if kind != "prose":
            block.append(line)
            if kind == "close":
                fences.append("\n".join(block))
                block = []
            continue
        if HEADING.match(line):
            headings.append(line)
            continue
        if TABLE_ROW.match(line):
            cells = _cells(line)
            if not _is_separator(cells):
                rows.append(cells)
            continue
        links.extend(LINK_DEST.findall(line))
    if tracker.active:
        fences.append("\n".join(block))

    return Digest(front, headings, fences, rows, links)


def diff_components(before: Digest, after: Digest) -> list:
    """The labels of the components that changed, in report order."""
    return [
        label
        for name, label in COMPONENTS
        if getattr(before, name) != getattr(after, name)
    ]
