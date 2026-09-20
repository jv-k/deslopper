"""Triage: ask Jev whether each finding is a tic to rewrite or a deliberate use to keep.

`run` takes the deterministic scan's result and the source text of the files it
flagged, and returns the same result with a verdict and probability on each
finding Jev answered. The exit code is not this module's concern: a verdict is
annotation, and the scan stays the gate.
"""

from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation

from . import jev
from .findings import LintResult, VERDICTS

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
    request that failed, and what the run spent."""

    result: LintResult
    errors: list = field(default_factory=list)
    tokens: int = 0
    cost: str = "0"

    @property
    def keep(self) -> int:
        return sum(1 for f in self.result.findings if f.verdict == "keep")

    @property
    def rewrite(self) -> int:
        return sum(1 for f in self.result.findings if f.verdict == "rewrite")


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


def _verdict(answer):
    """The (verdict, probability) pair from a choice answer, or None when the
    reply does not carry one Finding would accept."""
    if answer.kind != "choice" or answer.value not in VERDICTS:
        return None
    probability = answer.probabilities.get(answer.value)
    if not isinstance(probability, (int, float)) or not 0 <= probability <= 1:
        return None
    return answer.value, float(probability)


def require_key() -> None:
    """Raise JevUnavailable, naming the variable, when the gateway key is unset."""
    jev.require_key()


def read_sources(result: LintResult, items) -> dict:
    """The raw text of each file in `items` that has a finding, by display path.

    Files with no findings are never opened. A file that can no longer be read
    maps to empty text, so its findings go to Jev without context rather than
    not at all.
    """
    flagged = {f.path for f in result.findings}
    sources = {}
    for display, read_path in items:
        if display not in flagged:
            continue
        try:
            with open(read_path, encoding="utf-8", newline="\n") as fh:
                sources[display] = fh.read()
        except OSError:
            sources[display] = ""
    return sources


def run(result: LintResult, sources: dict) -> Triage:
    """Ask Jev about every finding in `result`, one request per file.

    `sources` maps a finding's path to that file's raw text. A file with no
    findings makes no request.
    """
    judged = list(result.findings)
    errors = []
    tokens = 0
    cost = Decimal(0)
    by_file = {}
    for index, finding in enumerate(result.findings):
        by_file.setdefault(finding.path, []).append(index)
    for path, indexes in by_file.items():
        lines = _lines(sources[path])
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
        for key, index in keyed.items():
            answer = reply.answers.get(key)
            pair = _verdict(answer) if answer is not None else None
            if pair is not None:
                judged[index] = replace(judged[index], verdict=pair[0], probability=pair[1])
    return Triage(
        result=LintResult(findings=judged, unreadable=list(result.unreadable)),
        errors=errors,
        tokens=tokens,
        cost=format(cost, "f"),
    )


def _decimal(cost) -> Decimal:
    """The gateway's cost as a Decimal, or zero when it sent none or garbage."""
    if cost is None:
        return Decimal(0)
    try:
        return Decimal(str(cost))
    except InvalidOperation:
        return Decimal(0)
