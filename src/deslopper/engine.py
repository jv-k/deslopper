"""The line scanner. A faithful port of the verified deslop-lint core."""

import re

from .findings import Finding, LintResult

FRONT_OPEN = re.compile(r"^---\s*$")
FRONT_CLOSE = re.compile(r"^(---|\.\.\.)\s*$")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
INLINE_CODE = re.compile(r"(`+).*?\1")
ENTITY = re.compile(r"&#?[0-9a-zA-Z]+;")
DISABLE_LINE = re.compile(r"<!--\s*deslop-lint-disable-line\b[^>]*-->")
DISABLE = re.compile(r"<!--\s*deslop-lint-disable\b[^>]*-->")
ENABLE = re.compile(r"<!--\s*deslop-lint-enable\b[^>]*-->")


def _blank(match: "re.Match") -> str:
    return " " * len(match.group(0))


def _run_tells(tells, text, path, ln):
    for tell in tells:
        n = 0
        for off in tell.matcher(text):
            yield Finding(path, ln, off + 1, tell.tier, tell.name, tell.message)
            n += 1
            if tell.scope == "first":
                break


def lint_file(display_path, read_path, pre_tells, post_tells):
    try:
        with open(read_path, encoding="utf-8", newline="\n") as fh:
            raw_lines = fh.readlines()
    except OSError:
        return [], False

    findings = []
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

        findings.extend(_run_tells(pre_tells, masked, display_path, ln))
        masked = ENTITY.sub(_blank, masked)
        findings.extend(_run_tells(post_tells, masked, display_path, ln))

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
