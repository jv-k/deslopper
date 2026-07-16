"""The line scanner. A faithful port of the verified deslop-lint core.

`scan_prose` owns the block structure: it decides which lines are prose (not front
matter, not fenced or inline code, not MDX ESM, not inside a disable region) and masks
what a tell must not see. `lint_file` is then a thin runner over the prose lines.
"""

import re
from dataclasses import dataclass

from .findings import Finding, LintResult

FRONT_OPEN = re.compile(r"^---\s*$")
FRONT_CLOSE = re.compile(r"^(---|\.\.\.)\s*$")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
INLINE_CODE = re.compile(r"(`+).*?\1")
ENTITY = re.compile(r"&#?[0-9a-zA-Z]+;")
DISABLE_LINE = re.compile(r"<!--\s*deslop-lint-disable-line\b[^>]*-->")
DISABLE = re.compile(r"<!--\s*deslop-lint-disable\b[^>]*-->")
ENABLE = re.compile(r"<!--\s*deslop-lint-enable\b[^>]*-->")
# In .mdx, a top-level line that starts with import/export is an ESM statement,
# not prose. Skip those lines so their punctuation is not scanned. JSX is left
# alone: it wraps rendered prose that should still be linted.
MDX_ESM = re.compile(r"^(import|export)\b")


def _blank(match: "re.Match") -> str:
    return " " * len(match.group(0))


@dataclass(frozen=True)
class ProseLine:
    """One prose line a tell sees: its 1-based number and the masked text for each phase.

    `pre_entity` has inline code blanked; `post_entity` has HTML entities blanked too.
    Both keep the original length, so a match offset is still the source column.
    """
    lineno: int
    pre_entity: str
    post_entity: str


def scan_prose(raw_lines, is_mdx=False):
    """Yield a ProseLine for each line that is prose, in order.

    Skips front matter, fenced code, MDX ESM statements, and disable regions, and masks
    inline code and HTML entities. Line endings on the input are tolerated, not required.
    """
    in_fence = False
    fence_marker = ""
    fence_len = 0
    in_front = False
    disabled = False
    first = True

    for ln, raw in enumerate(raw_lines, 1):
        line = raw[:-1] if raw.endswith("\n") else raw

        if first:
            first = False
            if FRONT_OPEN.match(line):
                in_front = True
                continue
        if in_front:
            if FRONT_CLOSE.match(line):
                in_front = False
            continue

        fence = FENCE.match(line)
        if fence:
            run = fence.group(1)
            ch, length = run[0], len(run)
            if not in_fence:
                in_fence, fence_marker, fence_len = True, ch, length
            elif ch == fence_marker and length >= fence_len:
                in_fence, fence_marker, fence_len = False, "", 0
            continue
        if in_fence:
            continue

        if is_mdx and MDX_ESM.match(line):
            continue

        masked = INLINE_CODE.sub(_blank, line)

        if DISABLE_LINE.search(masked):
            continue
        if DISABLE.search(masked):
            disabled = True
            continue
        if ENABLE.search(masked):
            disabled = False
            continue
        if disabled:
            continue

        yield ProseLine(ln, masked, ENTITY.sub(_blank, masked))


def _run_tells(tells, text, path, ln):
    for tell in tells:
        for off in tell.matcher(text):
            yield Finding(path, ln, off + 1, tell.tier, tell.name, tell.message)
            if tell.scope == "first":
                break


def lint_file(display_path, read_path, pre_tells, post_tells):
    try:
        with open(read_path, encoding="utf-8", newline="\n") as fh:
            raw_lines = fh.readlines()
    except OSError:
        return [], False

    findings = []
    for prose in scan_prose(raw_lines, display_path.endswith(".mdx")):
        findings.extend(_run_tells(pre_tells, prose.pre_entity, display_path, prose.lineno))
        findings.extend(_run_tells(post_tells, prose.post_entity, display_path, prose.lineno))
    return findings, True


def lint_files(items, tells) -> LintResult:
    pre = [t for t in tells if t.phase == "pre-entity"]
    post = [t for t in tells if t.phase != "pre-entity"]
    result = LintResult()
    for display_path, read_path in items:
        found, ok = lint_file(display_path, read_path, pre, post)
        if ok:
            result.findings.extend(found)
        else:
            result.unreadable.append(display_path)
    return result
