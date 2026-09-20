"""Triage: ask Jev whether each finding is a tic to rewrite or a deliberate use to keep.

`run` takes the deterministic scan's result and the source text of the files it
flagged, and returns the same result with a verdict and probability on each
finding Jev answered. The exit code is not this module's concern: a verdict is
annotation, and the scan stays the gate.
"""

from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation

from . import jev
from .findings import LintResult

FRAMING = (
    "These are lines of Markdown from software docs. A mechanical linter flagged "
    "each one for a named tell. Judge each finding on its own."
)
QUESTION = (
    "Finding {key}, the {name} tell at line {line}, column {col}: is the flagged "
    "text a machine-writing tic to rewrite, or a deliberate use to keep?"
)
OPTIONS = {
    "rewrite": (
        "a machine-writing tic: decorative punctuation, filler, puffery, or "
        "marketing cadence"
    ),
    "keep": (
        "a deliberate use: a quotation, proper noun, codename, field label, or "
        "punctuation joining two genuinely related clauses"
    ),
}


@dataclass
class Triage:
    """What a triage pass came back with: the judged result, one error line per
    request that failed or came back garbled, and what the run spent."""

    result: LintResult
    errors: list = field(default_factory=list)
    tokens: int = 0
    cost: Decimal = Decimal(0)


def _block(key, finding, lines) -> str:
    """One finding's block in the state: its key, tell, message, and the flagged
    line with one raw line above and below, marked so the model sees which."""
    out = [f"[{key}] tell: {finding.name} (column {finding.col})",
           f"message: {finding.message}"]
    index = finding.line - 1
    for i in range(max(index - 1, 0), min(index + 2, len(lines))):
        marker = ">" if i == index else " "
        out.append(f"{marker} {i + 1}: {lines[i]}")
    return "\n".join(out)


def _lines(text: str) -> list:
    """The file's lines, numbered the way the engine numbers them: split on "\\n"
    only, and a trailing newline ends the last line rather than opening an empty one."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _judge(finding, answer):
    """The finding with the answer's verdict, or None when the reply carried
    nothing Finding accepts. Finding is the one validator of the pair."""
    if answer is None:
        return None
    try:
        return replace(finding, verdict=answer.value,
                       probability=answer.probabilities.get(answer.value))
    except (ValueError, TypeError):
        return None


def _decimal(cost) -> Decimal:
    """The gateway's cost as a Decimal, or zero when it sent none or garbage."""
    if cost is None:
        return Decimal(0)
    try:
        return Decimal(str(cost))
    except InvalidOperation:
        return Decimal(0)


def run(result: LintResult, sources: dict) -> Triage:
    """Ask Jev about every finding in `result`, one request per file.

    `sources` maps a finding's path to that file's raw text. A file with no
    findings makes no request. A request that fails, or a reply missing usable
    answers, adds one line to `errors` and leaves those findings unjudged.
    """
    judged = list(result.findings)
    errors = []
    tokens = 0
    cost = Decimal(0)
    by_file = {}
    for index, finding in enumerate(result.findings):
        by_file.setdefault(finding.path, []).append(index)
    for path, indexes in by_file.items():
        lines = _lines(sources.get(path, ""))
        keyed = {f"f{n}": index for n, index in enumerate(indexes, 1)}
        state = "\n\n".join([FRAMING] + [
            _block(key, result.findings[index], lines) for key, index in keyed.items()
        ])
        questions = {
            key: jev.choice(QUESTION.format(key=key, name=result.findings[index].name,
                                            line=result.findings[index].line,
                                            col=result.findings[index].col), OPTIONS)
            for key, index in keyed.items()
        }
        try:
            reply = jev.evaluate(state, questions)
        except jev.JevError as exc:
            # One failed request never fails the lint: its findings stay
            # unjudged and the next file is still asked.
            errors.append(f"{path}: {exc}")
            continue
        tokens += (reply.input_tokens or 0) + (reply.output_tokens or 0)
        cost += _decimal(reply.market_cost)
        unusable = 0
        for key, index in keyed.items():
            finding = _judge(result.findings[index], reply.answers.get(key))
            if finding is None:
                unusable += 1
            else:
                judged[index] = finding
        if unusable:
            errors.append(
                f"{path}: the reply had no usable answer for {unusable} of {len(keyed)} findings"
            )
    return Triage(
        result=LintResult(findings=judged, unreadable=list(result.unreadable)),
        errors=errors,
        tokens=tokens,
        cost=cost,
    )
