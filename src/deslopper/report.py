"""Output formatting, the summary line, and the exit-code rule."""

import json
from decimal import ROUND_HALF_UP, Decimal

from . import gum, tiers, ui
from .findings import Finding


def _verdict_suffix(f: Finding) -> str:
    """The ` [keep 0.93]` tail a judged finding carries, or nothing for an unjudged one."""
    if f.verdict is None:
        return ""
    return f" [{f.verdict} {f.probability:.2f}]"


# The attended view is data: a list of lines, each a list of (style, text) parts, which
# gum.render draws in one call. A style is space-separated tokens: bold, faint, pill, and
# the palette's colour names (accent, error, warn, ok, muted, rule). "" is plain text.

BAR_SLOTS = 5
I_BAR = "❚"
I_CARET = "^"
# The rating that leads a judged row: the bar, " 0.93 ", and the verdict padded to "rewrite".
_RATING_WIDTH = BAR_SLOTS + 6 + 7
# Below this width the rating drops its probability: the bar and the verdict.
_COMPACT_BELOW = 64
_HINT_INDENT = 4
_ROW_INDENT = 6


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _tier_style(tier: str) -> str:
    return "error" if tier == "error" else "warn"


def _tier_mark(tier: str) -> tuple:
    return (_tier_style(tier), ui.I_ERROR if tier == "error" else ui.I_WARN)


def caught(text: str, col: int) -> str:
    """The text a tell caught at `col`: up to the next space, without trailing
    punctuation unless the punctuation is all there is, at most 24 characters."""
    rest = text[col - 1:]
    end = rest.find(" ")
    word = rest if end == -1 else rest[:end]
    word = word.rstrip(".,;:!?\"')") or word
    return word[:24] or rest[:1]


def excerpt(text: str, col: int, room: int) -> tuple:
    """The line around the caught text, cut to fit `room`: (before, caught, after).

    The caught text always shows. A cut side ends in an ellipsis, and the text after
    the catch gets the larger share, because it reads on from the tell."""
    word = caught(text, col)[:max(room - 2, 1)]
    before = text[:col - 1]
    after = text[col - 1 + len(word):]
    if len(before) + len(word) + len(after) <= room:
        return before, word, after
    keep_before = min(len(before), max((room - len(word)) // 3, room - len(word) - len(after)))
    if len(before) > keep_before:
        before = ("…" + before[len(before) - keep_before + 1:]) if keep_before > 0 else ""
    space = room - len(before) - len(word)
    if len(after) > space:
        after = (after[:space - 1] + "…") if space > 0 else ""
    return before, word, after


def _rating_parts(f: Finding, compact: bool) -> list:
    """Jev's rating: a five-slot bar in the confidence colour (ok from 0.9, warn from
    0.7, error below), then the probability, then the verdict. Compact drops the
    probability."""
    filled = round(f.probability * BAR_SLOTS)
    style = "ok" if f.probability >= 0.9 else "warn" if f.probability >= 0.7 else "error"
    parts = [(style, I_BAR * filled)]
    if filled < BAR_SLOTS:
        parts.append(("rule", I_BAR * (BAR_SLOTS - filled)))
    parts.append(("", " " if compact else f" {f.probability:.2f} "))
    parts.append(("bold" if f.verdict == "rewrite" else "faint", f.verdict))
    parts.append(("", " " * (7 - len(f.verdict))))
    return parts


def _right(left: list, right: list, width: int) -> list:
    """`left`, then `right` pushed to end at `width`, with at least two spaces between."""
    used = sum(len(t) for _s, t in left) + sum(len(t) for _s, t in right)
    return left + [("", " " * max(width - used, 2))] + right


def _header(command: str, linted: int, with_slop: int, width: int) -> list:
    left = [("", "  "), ("pill", " deslopper "), ("", " "), ("bold", command)]
    right = [("faint", f"{_plural(linted, 'file')}, {with_slop} with slop")]
    # Everything on the right ends where the rules end, two columns in from the edge.
    return [[], _right(left, right, width - 2), []]


def _tally(errors: int, warnings: int) -> list:
    parts = []
    if errors:
        parts.append(("error", _plural(errors, "error")))
    if warnings:
        parts += [("", "  ")] if parts else []
        parts.append(("warn", _plural(warnings, "warning")))
    return parts


def _rule(width: int) -> list:
    return [("", "  "), ("rule", "─" * (width - 4))]


def _group_lines(group: list, lines: list, loc_w: int, width: int, rated: bool) -> list:
    """One tell in one file: its name and count, its hint once, then a row per place
    with the caught text in its line and a caret under the first letter."""
    first = group[0]
    style = _tier_style(first.tier)
    head = [("", "  "), _tier_mark(first.tier), ("", " "), (f"bold {style}", first.name)]
    if len(group) > 1:
        head.append(("faint", f"  ×{len(group)}"))
    out = [head]
    for part in ui.wrap(width - _HINT_INDENT - 2, first.message):
        out.append([("", " " * _HINT_INDENT), ("muted", part)])
    compact = width < _COMPACT_BELOW
    lead_w = (_RATING_WIDTH - (5 if compact else 0) + 2) if rated else 0
    for f in group:
        row = [("", " " * _ROW_INDENT)]
        if rated:
            row += (_rating_parts(f, compact) + [("", "  ")] if f.verdict
                    else [("", " " * lead_w)])
        row.append(("faint", f"{f.line}:{f.col}".rjust(loc_w) + "  "))
        text = lines[f.line - 1] if 0 < f.line <= len(lines) else ""
        prefix = _ROW_INDENT + lead_w + loc_w + 2
        before, word, after = excerpt(text, f.col, max(width - prefix - 2, 8))
        row += [("muted", before), (f"bold {style}", word), ("muted", after)]
        out.append([p for p in row if p[1]])
        out.append([("", " " * (prefix + len(before))), (style, I_CARET)])
    return out


def lint_view(result, sources: dict, linted: int, width: int, judged=None,
              strict: bool = False, command: str = "lint") -> list:
    """The attended view of a lint run: a header, then a section per file with each
    tell grouped once under it, then the status line and the summary tables.

    `sources` maps a finding's path to the file's text, for the excerpts. `judged` is
    the Triage a --jev run returned; it adds the rating to each row, its failed requests
    to the footer, its verdicts to the summary table, and a table of what Jev cost and
    what the cache saved. Both tables span the rules' width."""
    findings = result.findings
    files = {}
    for f in findings:
        files.setdefault(f.path, []).append(f)
    out = _header(command, linted, len(files), width)
    tag = [("faint", "  [strict]")] if strict else []
    if not findings and not result.unreadable:
        return out + [[("", "  "), ("ok", f"{ui.I_OK} "), ("bold ok", "no slop found")] + tag, []]
    rated = any(f.verdict is not None for f in findings)
    loc_w = max((len(f"{f.line}:{f.col}") for f in findings), default=0)
    for path, fs in files.items():
        errors = sum(f.tier == "error" for f in fs)
        out.append(_right([("", "  "), ("bold accent", path)], _tally(errors, len(fs) - errors), width - 2))
        out.append(_rule(width))
        lines = _lines(sources.get(path, ""))
        groups = {}
        for f in fs:
            groups.setdefault(f.name, []).append(f)
        ordered = sorted(groups.values(), key=lambda g: (g[0].tier != "error", g[0].line, g[0].col))
        for i, group in enumerate(ordered):
            if i:
                out.append([])
            out += _group_lines(group, lines, loc_w, width, rated)
        out.append([])
    out.append(_rule(width))
    for path in result.unreadable:
        out.append([("", "  "), ("warn", f"{ui.I_TRACE} cannot read {path}")])
    for error in judged.errors if judged else ():
        out.append([("", "  "), ("error", f"{ui.I_ERROR} Jev skipped {error}")])
    status = ([("error", f"{ui.I_ERROR} "), ("bold error", _plural(result.errors, "error"))]
              if result.errors else [("ok", f"{ui.I_OK} "), ("bold ok", "no errors")])
    if result.warnings:
        status += [("", "   "), ("warn", f"{ui.I_WARN} "), ("bold warn", _plural(result.warnings, "warning"))]
    out.append([("", "  ")] + status + tag)
    out += [[], summary_table(result, judged, len(files), width - 4)]
    if judged is not None:
        out.append(jev_table(result, judged, width - 4))
    return out + [[]]


def _money(cost) -> str:
    """A cost to two significant figures, which is all a glance needs; the json
    format keeps the exact cost."""
    if not cost:
        return "$0"
    rounded = cost.quantize(Decimal(1).scaleb(cost.adjusted() - 1), rounding=ROUND_HALF_UP)
    return f"${rounded.normalize():f}"


def summary_table(result, judged, with_slop: int, width: int) -> gum.Table:
    """The run's totals as label and value rows, `width` across: the findings, and
    after a --jev run, Jev's verdicts."""
    rows = [("findings", [("bold", f"{len(result.findings)} in {_plural(with_slop, 'file')}")]),
            ("errors", [("error" if result.errors else "faint", str(result.errors))]),
            ("warnings", [("warn" if result.warnings else "faint", str(result.warnings))])]
    if result.unreadable:
        rows.append(("unreadable", [("warn", str(len(result.unreadable)))]))
    if judged is not None:
        rows += [("rewrite", [("bold", str(result.rewrite))]),
                 ("keep", [("", str(result.keep))])]
    return gum.Table(columns=["summary", ""], width=width,
                     rows=[[[("muted", label)], value] for label, value in rows])


def jev_table(result, judged, width: int) -> gum.Table:
    """What Jev cost, `width` across: the verdicts asked for on this run with their
    tokens and cost, then the verdicts the cache answered with what they cost when
    Jev first gave them. The cache keeps no cost for a verdict stored before it
    recorded one."""
    asked = result.rewrite + result.keep - judged.cached
    if judged.cached and not (judged.saved_tokens or judged.saved_cost):
        saved = [[("faint", "unknown")], [("faint", "unknown")]]
    else:
        style = "ok" if judged.cached else ""
        saved = [[(style, f"{judged.saved_tokens:,}")], [(style, _money(judged.saved_cost))]]
    rows = [[[("muted", "this run")], [("", str(asked))], [("", f"{judged.tokens:,}")],
             [("", _money(judged.cost))]],
            [[("muted", "cache saved")], [("ok" if judged.cached else "", str(judged.cached))]]
            + saved]
    return gum.Table(columns=["Jev", "verdicts", "tokens", "cost"], rows=rows, width=width)


def _lines(text: str) -> list:
    """The file's lines, numbered as the engine numbers them."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def rule_lines(tells, width: int) -> list:
    """The attended rules view: one aligned row per tell, the message after it, or
    below it when the terminal is too narrow for a column."""
    name_w = max(len(t.name) for t in tells)
    phase_w = max(len(t.phase) for t in tells)
    scope_w = max(len(t.scope) for t in tells)
    column = 2 + name_w + 2 + 9 + phase_w + 1 + scope_w + 2
    room = width - column
    out = []
    for t in tells:
        style = _tier_style(t.tier)
        row = [("", "  "), ("bold", t.name), ("", " " * (name_w - len(t.name) + 2)),
               (style, f"{ui.I_ERROR} error" if t.tier == "error" else f"{ui.I_WARN} warn"),
               ("", "  " if t.tier == "error" else "   "),
               ("faint", t.phase.ljust(phase_w) + " " + t.scope.ljust(scope_w)), ("", "  ")]
        if room >= 20:
            parts = ui.wrap(room, t.message) or [""]
            out.append(row + [("", parts[0])])
            out += [[("", " " * column), ("", part)] for part in parts[1:]]
        else:
            out.append(row[:-1])
            out += [[("", "      "), ("", part)] for part in ui.wrap(max(width - 8, 20), t.message)]
    return out


def format_text(result) -> str:
    """One `path:line:col [tier] name: message` line per finding, the pinned grammar,
    with the ` [keep 0.93]` tail on a judged finding."""
    lines = [
        f"{f.path}:{f.line}:{f.col} [{f.tier}] {f.name}: {f.message}{_verdict_suffix(f)}"
        for f in result.findings
    ]
    return "\n".join(lines) + ("\n" if lines else "")


def _encode(message: str) -> str:
    return message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _encode_prop(value: str) -> str:
    # A property value escapes as the data does, plus the ':' and ',' that delimit the
    # command's properties. A path with either would otherwise truncate the annotation.
    return _encode(value).replace(":", "%3A").replace(",", "%2C")


def format_github(result) -> str:
    lines = []
    for f in result.findings:
        level = tiers.github_level(f.tier)
        lines.append(
            f"::{level} file={_encode_prop(f.path)},line={f.line},col={f.col}::"
            f"{f.name} - {_encode(f.message + _verdict_suffix(f))}"
        )
    return "\n".join(lines) + ("\n" if lines else "")


def _finding_json(f: Finding) -> dict:
    item = {"path": f.path, "line": f.line, "col": f.col,
            "tier": f.tier, "name": f.name, "message": f.message}
    if f.verdict is not None:
        item["verdict"] = f.verdict
        item["probability"] = f.probability
    return item


def format_json(result, judged=None) -> str:
    """The json payload. `judged` is the Triage a --jev run returned, which adds the
    `jev` object with its totals and the requests that failed."""
    payload = {
        "findings": [_finding_json(f) for f in result.findings],
        "unreadable": list(result.unreadable),
        "summary": {
            "errors": result.errors,
            "warnings": result.warnings,
            "unreadable": len(result.unreadable),
        },
    }
    if judged is not None:
        payload["jev"] = {
            "keep": result.keep,
            "rewrite": result.rewrite,
            "cached": judged.cached,
            "saved_tokens": judged.saved_tokens,
            "saved_cost": f"{judged.saved_cost:f}",
            "tokens": judged.tokens,
            "cost": f"{judged.cost:f}",
            "errors": list(judged.errors),
        }
    return json.dumps(payload, indent=2) + "\n"


def _triage_tail(result, judged) -> str:
    """The ` · triage: N keep, M rewrite · T tokens, $C` tail when triage ran, with
    `, K cached` after the verdicts when the cache answered any, and
    ` · saved T tokens, $C` after the spend when the cache recorded what it saved.

    `judged` is the Triage the pass returned, whose result is `result`."""
    if judged is None:
        return ""
    cached = f", {judged.cached} cached" if judged.cached else ""
    saved = (f" · saved {judged.saved_tokens} tokens, ${judged.saved_cost:f}"
             if judged.saved_tokens or judged.saved_cost else "")
    return (f" · triage: {result.keep} keep, {result.rewrite} rewrite{cached}"
            f" · {judged.tokens} tokens, ${judged.cost:f}{saved}")


def summary_line(result, strict: bool, judged=None) -> str:
    """The run's one summary line, with its status icon."""
    tag = " [strict]" if strict else ""
    unreadable = len(result.unreadable)
    if not result.findings and not unreadable:
        return f"{ui.I_OK} no slop found{tag}"
    counts = f"{result.errors} error(s), {result.warnings} warning(s)"
    if unreadable:
        counts += f", {unreadable} unreadable"
    counts += _triage_tail(result, judged)
    icon = ui.I_ERROR if result.errors or unreadable else ui.I_WARN
    return f"{icon} {counts}{tag}"


def exit_code(result, strict: bool) -> int:
    fail = bool(result.unreadable) or any(
        tiers.is_failing(f.tier, strict) for f in result.findings
    )
    return 1 if fail else 0
