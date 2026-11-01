"""Triage: ask Jev whether each smell is a tic to rewrite or a deliberate use to keep.

`run` takes the deterministic scan's result and the source text of the files it
flagged, and returns the same result with a verdict and probability on each
smell Jev answered. The exit code is not this module's concern: a verdict is
annotation, and the scan stays the gate.

With a cache, a smell Jev answered before is not asked about again while its
tell, message, column and the lines around it are unchanged. The line number is
left out of the key, so a smell that only moved down the file still hits. Each
stored verdict keeps its share of the request that answered it, so a hit can count
what it saved.
"""

import json
from contextlib import nullcontext
from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation
from typing import NamedTuple

from . import jev
from .smells import LintResult

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

# A failed request's error line names at most this many of its files, then counts the rest.
NAMED_FILES = 3


class Pending(NamedTuple):
    """A smell still to send: its place in the result, its cache key, and its file's lines."""

    index: int
    cache_key: object
    lines: list


@dataclass
class Triage:
    """What a triage pass came back with: the judged result, one error line per
    request that failed or came back garbled, what the run spent, how many verdicts
    came from the cache, and what those verdicts cost when Jev first gave them."""

    result: LintResult
    errors: list = field(default_factory=list)
    tokens: int = 0
    cost: Decimal = Decimal(0)
    cached: int = 0
    saved_tokens: int = 0
    saved_cost: Decimal = Decimal(0)


def _block(key, smell, lines) -> str:
    """One smell's block in the state: its key, tell, message, and the flagged
    line with one raw line above and below, marked so the model sees which."""
    out = [f"[{key}] tell: {smell.name} (column {smell.col})",
           f"message: {smell.message}"]
    index = smell.line - 1
    for i in range(max(index - 1, 0), min(index + 2, len(lines))):
        marker = ">" if i == index else " "
        out.append(f"{marker} {i + 1}: {lines[i]}")
    return "\n".join(out)


def _cache_key(smell, lines):
    """What a verdict depends on, without the line number: the prompt, the tell, and
    the flagged line with its neighbours. None when there is no source text, since
    a smell with no context says too little to share an answer."""
    index = smell.line - 1
    context = [[i == index, lines[i]] for i in range(max(index - 1, 0), min(index + 2, len(lines)))]
    if not context:
        return None
    return {"version": CACHE_VERSION, "model": jev.MODEL, "framing": FRAMING,
            "question": QUESTION, "options": OPTIONS, "tell": smell.name,
            "message": smell.message, "col": smell.col, "context": context}


def _recall(cache, key, smell):
    """The cache entry for `smell`, as the smell with its verdict and the share of
    tokens and cost it saved, or None on a miss or an entry Smell rejects. An entry
    with no share, or a garbled one, saved nothing that can be counted."""
    if cache is None or key is None:
        return None
    entry = cache.get(key)
    if not isinstance(entry, dict):
        return None
    try:
        hit = replace(smell, verdict=entry.get("verdict"), probability=entry.get("probability"))
    except (ValueError, TypeError):
        return None
    tokens = entry.get("tokens")
    if isinstance(tokens, bool) or not isinstance(tokens, int) or tokens < 0:
        tokens = 0
    cost = _decimal(entry.get("cost"))
    return hit, tokens, cost if cost.is_finite() and cost >= 0 else Decimal(0)


def _shares(tokens: int, cost: Decimal, count: int) -> list:
    """One request's spend split evenly over its `count` smells, as (tokens, cost)
    pairs. The token remainder goes to the first shares, so the shares add up to the
    request. The cost is cut to the nano-dollar, finer than the gateway reports."""
    base, extra = divmod(tokens, count)
    each = (cost / count).quantize(Decimal("1e-9"))
    return [(base + (i < extra), each) for i in range(count)]


def _lines(text: str) -> list:
    """The file's lines, numbered the way the engine numbers them: split on "\\n"
    only, and a trailing newline ends the last line rather than opening an empty one."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _judge(smell, answer):
    """The smell with the answer's verdict, or None when the reply carried
    nothing Smell accepts. Smell is the one validator of the pair."""
    if answer is None:
        return None
    try:
        return replace(smell, verdict=answer.value,
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


def _state(blocks) -> str:
    """The state one request sends: the framing, then each smell's block."""
    return "\n\n".join([FRAMING] + blocks)


def _question(key, smell) -> dict:
    """The one question a request asks about `smell`, under its block's key."""
    return jev.choice(QUESTION.format(key=key, name=smell.name, line=smell.line, col=smell.col),
                      OPTIONS)


def _batches(smells, pending, budget, question_budget) -> list:
    """`pending` in file order, packed into as few batches as fit under `budget`
    characters of state and `question_budget` characters of questions, as the JSON
    the request sends. Each batch maps a question key, f1, f2, ... in order, to the
    pending smell, its block and its question, so the block's label and its
    question's key are the one string. A batch closes when the next smell would
    take it over either budget. A smell over a budget on its own still goes, alone
    in its batch, since cutting it would part a smell from its context."""
    batches = []
    size = 0
    asked = 0
    for item in pending:
        smell = smells[item.index]
        batch = batches[-1] if batches else None
        if batch:
            key = f"f{len(batch) + 1}"
            block = _block(key, smell, item.lines)
            question = _question(key, smell)
            # One entry's share of the questions' JSON. The shares of a map add
            # up to the length of the map's own JSON.
            cost = len(json.dumps({key: question}))
            if size + 2 + len(block) <= budget and asked + cost <= question_budget:
                batch[key] = (item, block, question)
                size += 2 + len(block)
                asked += cost
                continue
        block = _block("f1", smell, item.lines)
        question = _question("f1", smell)
        batches.append({"f1": (item, block, question)})
        size = len(_state([block]))
        asked = len(json.dumps({"f1": question}))
    return batches


def _named(files) -> str:
    """A failed batch's files for its error line: the first few, then a count of the rest."""
    if len(files) <= NAMED_FILES:
        return ", ".join(files)
    return f"{', '.join(files[:NAMED_FILES])} and {len(files) - NAMED_FILES} more files"


def run(result: LintResult, sources: dict, progress=None, cache=None) -> Triage:
    """Ask Jev about every smell in `result`, packed into as few requests as fit.

    `sources` maps a smell's path to that file's raw text. Smells are packed in
    file order under `jev.STATE_CHAR_BUDGET` of state and `jev.QUESTION_CHAR_BUDGET`
    of questions, across files and splitting a file when it runs over, so each
    smell is in exactly one request. A file with no
    smells adds nothing. A request that fails, or a reply missing usable answers,
    adds one line to `errors`, prefixed with the batch's first files, and leaves those
    smells unjudged. The next request is still sent.
    `progress(where, count, index, total)`, when given, returns a context that
    wraps each request, which is how the CLI shows a spinner per request. Its
    `where` is the file's path when the request holds one file, else "N files".
    `cache`, when given, is a `cache.Store`: a smell it holds a verdict for is
    judged from it and never sent, and each usable answer Jev gives is stored.
    """
    judged = list(result.smells)
    errors = []
    tokens = 0
    cost = Decimal(0)
    cached = 0
    saved_tokens = 0
    saved_cost = Decimal(0)
    by_file = {}
    for index, smell in enumerate(result.smells):
        by_file.setdefault(smell.path, []).append(index)
    pending = []
    for path, indexes in by_file.items():
        lines = _lines(sources.get(path, ""))
        for index in indexes:
            key = _cache_key(result.smells[index], lines) if cache is not None else None
            hit = _recall(cache, key, result.smells[index])
            if hit is None:
                pending.append(Pending(index, key, lines))
            else:
                judged[index], hit_tokens, hit_cost = hit
                cached += 1
                saved_tokens += hit_tokens
                saved_cost += hit_cost
    batches = _batches(result.smells, pending, jev.STATE_CHAR_BUDGET, jev.QUESTION_CHAR_BUDGET)
    for number, batch in enumerate(batches, 1):
        files = list(dict.fromkeys(result.smells[item.index].path for item, _, _ in batch.values()))
        state = _state([block for _, block, _ in batch.values()])
        questions = {key: question for key, (_, _, question) in batch.items()}
        label = files[0] if len(files) == 1 else f"{len(files)} files"
        wrap = progress(label, len(batch), number, len(batches)) if progress else nullcontext()
        try:
            with wrap:
                reply = jev.evaluate(state, questions)
        except jev.JevError as exc:
            # One failed request never fails the lint: its smells stay
            # unjudged and the next batch is still asked.
            errors.append(f"{_named(files)}: {exc}")
            continue
        spent = (reply.input_tokens or 0) + (reply.output_tokens or 0)
        price = _decimal(reply.market_cost)
        tokens += spent
        cost += price
        unusable = 0
        shares = _shares(spent, price, len(batch))
        for (key, (item, _, _)), (share_tokens, share_cost) in zip(batch.items(), shares):
            index, cache_key = item.index, item.cache_key
            smell = _judge(result.smells[index], reply.answers.get(key))
            if smell is None:
                unusable += 1
                continue
            judged[index] = smell
            if cache is not None and cache_key is not None:
                cache.put(cache_key, {"verdict": smell.verdict,
                                      "probability": smell.probability,
                                      "tokens": share_tokens, "cost": f"{share_cost:f}"})
        if unusable:
            errors.append(
                f"{_named(files)}: the reply had no usable answer for {unusable} of {len(batch)} smells"
            )
    return Triage(
        result=LintResult(smells=judged, unreadable=list(result.unreadable)),
        errors=errors,
        tokens=tokens,
        cost=cost,
        cached=cached,
        saved_tokens=saved_tokens,
        saved_cost=saved_cost,
    )
