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
# A fence is indented at most 3 spaces (4+ is indented code, not a fence); the rest of
# the line is the info string. `scan_prose` applies the CommonMark opener/closer rules.
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
# A code span opens on a maximal backtick run and closes on a run of the exact same
# length. The lookarounds keep the closer maximal, so a 2-backtick opener is not closed
# by two of a longer run, which would mask the prose between as code.
INLINE_CODE = re.compile(r"(?<!`)(`+).*?(?<!`)\1(?!`)")
ENTITY = re.compile(r"&#?[0-9a-zA-Z]+;")
# The directive is exactly `-disable-line`, `-disable`, or `-enable`; the lookaheads stop
# an unknown suffix (`-disable-next-line`, `-disable-line-foo`) from matching any of them.
DISABLE_LINE = re.compile(r"<!--\s*deslop-lint-disable-line(?![-\w])[^>]*-->")
DISABLE = re.compile(r"<!--\s*deslop-lint-disable(?![-\w])[^>]*-->")
ENABLE = re.compile(r"<!--\s*deslop-lint-enable(?![-\w])[^>]*-->")
# In .mdx, a top-level line that starts with import/export is an ESM statement,
# not prose. Skip those lines so their punctuation is not scanned. JSX is left
# alone: it wraps rendered prose that should still be linted.
MDX_ESM = re.compile(r"^(import|export)\b")


def _blank(match: "re.Match") -> str:
    return " " * len(match.group(0))


class FenceTracker:
    """The fenced-code state machine, shared by the scanner and the digest.

    Feed lines in order; each is classified as 'open', 'inside', 'close', or
    'prose'. An invalid opener (a backtick fence with a backtick in its info
    string) classifies as prose, per CommonMark.
    """

    def __init__(self):
        self.active = False
        self._marker = ""
        self._length = 0

    def feed(self, line: str) -> str:
        fence = FENCE.match(line)
        if self.active:
            if fence:
                run, rest = fence.group(1), fence.group(2)
                # Only a bare run of the same char, at least as long, closes the block.
                if run[0] == self._marker and len(run) >= self._length and not rest.strip():
                    self.active = False
                    return "close"
            return "inside"
        if fence:
            run, rest = fence.group(1), fence.group(2)
            if run[0] != "`" or "`" not in rest:
                self.active, self._marker, self._length = True, run[0], len(run)
                return "open"
        return "prose"


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
    fences = FenceTracker()
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

        if fences.feed(line) != "prose":
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
