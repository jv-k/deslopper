"""Output formatting, the summary line, and the exit-code rule."""

import json

from . import tiers, ui


def tier_style(pal, tier):
    return pal.error if tier == "error" else pal.warn


def format_text(result, pal=ui.PLAIN) -> str:
    # With the plain palette every sequence is empty, so the line collapses to
    # the pinned `path:line:col [tier] name: message` grammar byte for byte.
    lines = [
        f"{pal.bold}{f.path}{pal.reset}:{f.line}:{f.col} "
        f"{tier_style(pal, f.tier)}[{f.tier}]{pal.reset} "
        f"{f.name}: {pal.dim}{f.message}{pal.reset}"
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
            f"{f.name} - {_encode(f.message)}"
        )
    return "\n".join(lines) + ("\n" if lines else "")


def format_json(result) -> str:
    payload = {
        "findings": [
            {"path": f.path, "line": f.line, "col": f.col,
             "tier": f.tier, "name": f.name, "message": f.message}
            for f in result.findings
        ],
        "unreadable": list(result.unreadable),
        "summary": {
            "errors": result.errors,
            "warnings": result.warnings,
            "unreadable": len(result.unreadable),
        },
    }
    return json.dumps(payload, indent=2) + "\n"


def summary_line(result, strict: bool, pal=ui.PLAIN) -> str:
    tag = " [strict]" if strict else ""
    unreadable = len(result.unreadable)
    if not result.findings and not unreadable:
        return ui.status_line(pal, pal.ok, ui.I_OK, f"no slop found{tag}")
    counts = f"{result.errors} error(s), {result.warnings} warning(s)"
    if unreadable:
        counts += f", {unreadable} unreadable"
    if result.errors or unreadable:
        return ui.status_line(pal, pal.error, ui.I_ERROR, f"{counts}{tag}")
    return ui.status_line(pal, pal.warn, ui.I_WARN, f"{counts}{tag}")


def exit_code(result, strict: bool) -> int:
    fail = bool(result.unreadable) or any(
        tiers.is_failing(f.tier, strict) for f in result.findings
    )
    return 1 if fail else 0
