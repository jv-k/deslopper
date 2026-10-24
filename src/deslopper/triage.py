"""Triage: ask Jev whether each finding is a tic to rewrite or a deliberate use to keep.

`run` takes the deterministic scan's result and the source text of the files it
flagged, and returns the same result with a verdict and probability on each
finding Jev answered. The exit code is not this module's concern: a verdict is
annotation, and the scan stays the gate.

With a cache, a finding Jev answered before is not asked about again while its
tell, message, column and the lines around it are unchanged. The line number is
left out of the key, so a finding that only moved down the file still hits.
"""

from contextlib import nullcontext
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

# Bump to drop every cached verdict, for a change the key cannot see.
CACHE_VERSION = 1


@dataclass
class Triage:
    """What a triage pass came back with: the judged result, one error line per
    request that failed or came back garbled, what the run spent, and how many
    verdicts came from the cache."""

    result: LintResult
    errors: list = field(default_factory=list)
    tokens: int = 0
    cost: Decimal = Decimal(0)
    cached: int = 0


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


def _cache_key(finding, lines):
    """What a verdict depends on, without the line number: the prompt, the tell, and
    the flagged line with its neighbours. None when there is no source text, since
    a finding with no context says too little to share an answer."""
    index = finding.line - 1
    context = [[i == index, lines[i]] for i in range(max(index - 1, 0), min(index + 2, len(lines)))]
    if not context:
        return None
    return {"version": CACHE_VERSION, "model": jev.MODEL, "framing": FRAMING,
            "question": QUESTION, "options": OPTIONS, "tell": finding.name,
            "message": finding.message, "col": finding.col, "context": context}


def _recall(cache, key, finding):
    """The finding with its cached verdict, or None on a miss or an entry Finding rejects."""
    if cache is None or key is None:
        return None
    entry = cache.get(key)
    if not isinstance(entry, dict):
        return None
    try:
        return replace(finding, verdict=entry.get("verdict"), probability=entry.get("probability"))
    except (ValueError, TypeError):
        return None


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


def run(result: LintResult, sources: dict, progress=None, cache=None) -> Triage:
    """Ask Jev about every finding in `result`, one request per file.

    `sources` maps a finding's path to that file's raw text. A file with no
    findings makes no request. A request that fails, or a reply missing usable
    answers, adds one line to `errors` and leaves those findings unjudged.
    `progress(path, count, index, total)`, when given, returns a context that
    wraps each request, which is how the CLI shows a spinner per file.
    `cache`, when given, is a `cache.Store`: a finding it holds a verdict for is
    judged from it, a file whose findings are all held makes no request, and each
    usable answer Jev gives is stored.
    """
    judged = list(result.findings)
    errors = []
    tokens = 0
    cost = Decimal(0)
    cached = 0
    by_file = {}
    for index, finding in enumerate(result.findings):
        by_file.setdefault(finding.path, []).append(index)
    asking = {}
    for path, indexes in by_file.items():
        lines = _lines(sources.get(path, ""))
        for index in indexes:
            key = _cache_key(result.findings[index], lines) if cache is not None else None
            hit = _recall(cache, key, result.findings[index])
            if hit is None:
                asking.setdefault(path, (lines, []))[1].append((index, key))
            else:
                judged[index] = hit
                cached += 1
    for number, (path, (lines, pending)) in enumerate(asking.items(), 1):
        keyed = {f"f{n}": item for n, item in enumerate(pending, 1)}
        state = "\n\n".join([FRAMING] + [
            _block(key, result.findings[index], lines) for key, (index, _) in keyed.items()
        ])
        questions = {
            key: jev.choice(QUESTION.format(key=key, name=result.findings[index].name,
                                            line=result.findings[index].line,
                                            col=result.findings[index].col), OPTIONS)
            for key, (index, _) in keyed.items()
        }
        wrap = progress(path, len(pending), number, len(asking)) if progress else nullcontext()
        try:
            with wrap:
                reply = jev.evaluate(state, questions)
        except jev.JevError as exc:
            # One failed request never fails the lint: its findings stay
            # unjudged and the next file is still asked.
            errors.append(f"{path}: {exc}")
            continue
        tokens += (reply.input_tokens or 0) + (reply.output_tokens or 0)
        cost += _decimal(reply.market_cost)
        unusable = 0
        for key, (index, cache_key) in keyed.items():
            finding = _judge(result.findings[index], reply.answers.get(key))
            if finding is None:
                unusable += 1
                continue
            judged[index] = finding
            if cache is not None and cache_key is not None:
                cache.put(cache_key, {"verdict": finding.verdict,
                                      "probability": finding.probability})
        if unusable:
            errors.append(
                f"{path}: the reply had no usable answer for {unusable} of {len(keyed)} findings"
            )
    return Triage(
        result=LintResult(findings=judged, unreadable=list(result.unreadable)),
        errors=errors,
        tokens=tokens,
        cost=cost,
        cached=cached,
    )
