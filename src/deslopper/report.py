"""Output formatting, the summary line, and the exit-code rule."""

import json

_LEVEL = {"error": "error", "warn": "warning"}


def format_text(result) -> str:
    lines = [
        f"{f.path}:{f.line}:{f.col} [{f.tier}] {f.name}: {f.message}"
        for f in result.findings
    ]
    return "\n".join(lines) + ("\n" if lines else "")


def _encode(message: str) -> str:
    return message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def format_github(result) -> str:
    lines = []
    for f in result.findings:
        level = _LEVEL[f.tier]
        lines.append(
            f"::{level} file={f.path},line={f.line},col={f.col}::"
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


def summary_line(result, strict: bool) -> str:
    tag = " [strict]" if strict else ""
    return (
        f"deslopper: {result.errors} error(s), {result.warnings} warning(s), "
        f"{len(result.unreadable)} unreadable{tag}"
    )


def exit_code(result, strict: bool) -> int:
    fail = result.errors > 0 or bool(result.unreadable) or (strict and result.warnings > 0)
    return 1 if fail else 0
