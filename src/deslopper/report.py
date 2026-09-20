"""Output formatting, the summary line, and the exit-code rule."""

import json

from . import tiers, ui
from .findings import Finding


def tier_style(pal, tier):
    return pal.error if tier == "error" else pal.warn


def _verdict_suffix(f: Finding, pal=ui.PLAIN) -> str:
    """The ` [keep 0.93]` tail a judged finding carries, or nothing for an unjudged one.
    Styled, the probability leads the line as a rating bar instead, and only the verdict
    stays in the tail; piped output keeps the number so the grammar stays pinned."""
    if f.verdict is None:
        return ""
    if pal.enabled:
        return f" [{f.verdict}]"
    return f" [{f.verdict} {f.probability:.2f}]"


def _rating_prefix(f: Finding, pal) -> str:
    """The bar that leads a judged line, or blank padding of the same width so the paths
    of a run's unjudged findings still line up."""
    if f.verdict is None:
        return " " * (ui.BAR_SLOTS + 1)
    return f"{ui.rating_bar(pal, f.probability)} "


def format_text(result, pal=ui.PLAIN) -> str:
    # With the plain palette every sequence is empty, so the line collapses to
    # the pinned `path:line:col [tier] name: message` grammar byte for byte.
    # The rating column appears only styled, and only once something was judged.
    rated = pal.enabled and any(f.verdict is not None for f in result.findings)
    lines = [
        f"{_rating_prefix(f, pal) if rated else ''}"
        f"{pal.bold}{f.path}{pal.reset}:{f.line}:{f.col} "
        f"{tier_style(pal, f.tier)}[{f.tier}]{pal.reset} "
        f"{f.name}: {pal.dim}{f.message}{pal.reset}{_verdict_suffix(f, pal)}"
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


def format_json(result) -> str:
    payload = {
        "findings": [_finding_json(f) for f in result.findings],
        "unreadable": list(result.unreadable),
        "summary": {
            "errors": result.errors,
            "warnings": result.warnings,
            "unreadable": len(result.unreadable),
        },
    }
    return json.dumps(payload, indent=2) + "\n"


def _triage_tail(result, judged) -> str:
    """The ` · triage: N keep, M rewrite · T tokens, $C` tail when triage ran.

    `judged` is the Triage the pass returned, whose result is `result`."""
    if judged is None:
        return ""
    return (f" · triage: {result.keep} keep, {result.rewrite} rewrite"
            f" · {judged.tokens} tokens, ${judged.cost:f}")


def summary_line(result, strict: bool, pal=ui.PLAIN, judged=None) -> str:
    tag = " [strict]" if strict else ""
    unreadable = len(result.unreadable)
    if not result.findings and not unreadable:
        return ui.status_line(pal, pal.ok, ui.I_OK, f"no slop found{tag}")
    counts = f"{result.errors} error(s), {result.warnings} warning(s)"
    if unreadable:
        counts += f", {unreadable} unreadable"
    counts += _triage_tail(result, judged)
    if result.errors or unreadable:
        return ui.status_line(pal, pal.error, ui.I_ERROR, f"{counts}{tag}")
    return ui.status_line(pal, pal.warn, ui.I_WARN, f"{counts}{tag}")


def exit_code(result, strict: bool) -> int:
    fail = bool(result.unreadable) or any(
        tiers.is_failing(f.tier, strict) for f in result.findings
    )
    return 1 if fail else 0
