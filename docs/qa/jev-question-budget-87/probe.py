"""Measure how the questions in a triage request use Jev's window (issue #87).

Run from the repo root with the gateway key exported. Each request costs a fraction
of a cent:

    .venv/bin/python docs/qa/jev-question-budget-87/probe.py

It sends real triage requests, built by `triage._block`, `triage._state` and the
triage question, and records for each one the characters of state, the characters
of the questions as JSON, and the input and output tokens the gateway reports. The
sweeps grow the question count on short findings, then the questions alone, then
the findings' blocks alone, then one padded line of state, so the tokens per
character of each part can be read off. Two bisections then find the largest
request the gateway accepts: one by question count on short findings, one by the
length of a state with one question. The check at the end packs findings with
`triage._batches` under the shipped budgets and sends the first, fullest batch,
once for short findings and twice for findings sized to fill both budgets
together. Results go to `results.json` beside this file.
"""
import json
import sys
from pathlib import Path

from deslopper import jev, triage
from deslopper.smells import Smell

HERE = Path(__file__).resolve().parent
SMELL = Smell("a.md", 1, 1, "warn", "semicolon", "semicolon in prose, use a full stop")


def request(count, line="a short flagged line; tail"):
    """A triage request of `count` short findings, as `triage.run` builds it."""
    blocks, questions = [], {}
    for i in range(1, count + 1):
        key = f"f{i}"
        blocks.append(triage._block(key, SMELL, [f"{i} {line}"]))
        questions[key] = jev.choice(
            triage.QUESTION.format(key=key, name=SMELL.name, line=1, col=1), triage.OPTIONS)
    return {"model": jev.MODEL, "state": triage._state(blocks), "questions": questions}


def padded(state_chars):
    """One finding whose flagged line is padded so the state is `state_chars` long."""
    body = request(1)
    extra = max(state_chars - len(body["state"]), 0)
    words = ("plain words in a long line of docs " * (extra // 35 + 1))[:extra]
    return request(1, line="a short flagged line; " + words)


def packed(count, width, fill="w"):
    """The first batch `triage._batches` packs from `count` findings in one file,
    each flagged line about `width` characters long, under the shipped budgets. A
    fill of one repeated letter is the densest state per token the probe found;
    a fill of words is closer to prose."""
    pad = (fill * width)[:width]
    text = "".join(f"{n:05d} {pad}; tail\n" for n in range(1, count + 1))
    lines = triage._lines(text)
    smells = [Smell("a.md", n, 1, "warn", SMELL.name, SMELL.message) for n in range(1, count + 1)]
    pending = [triage.Pending(i, None, lines) for i in range(count)]
    batch = triage._batches(smells, pending, jev.STATE_CHAR_BUDGET, jev.QUESTION_CHAR_BUDGET)[0]
    return {"model": jev.MODEL, "state": triage._state([b for _, b, _ in batch.values()]),
            "questions": {key: q for key, (_, _, q) in batch.items()}}


def send(label, body):
    row = {"label": label, "questions": len(body["questions"]),
           "state_chars": len(body["state"]),
           "question_chars": len(json.dumps(body["questions"]))}
    try:
        reply = jev.post(body)
    except jev.JevError as err:
        row["error"] = str(err)
    else:
        usage = reply.get("usage") or {}
        row["input_tokens"] = usage.get("inputTokens")
        row["output_tokens"] = usage.get("outputTokens")
        row["answers"] = len(reply.get("answers") or {})
    print(json.dumps(row), flush=True)
    return row


def bisect(label, build, lo, hi, step, rows):
    """The largest `build(n)` between `lo` and `hi` the gateway accepts, to `step`."""
    while hi - lo > step:
        mid = (lo + hi) // 2
        row = send(label, build(mid))
        rows.append(row)
        if "error" in row:
            hi = mid
        else:
            lo = mid
    return lo


def questions_only(count):
    """`count` questions about the state of one finding: the questions' own tokens."""
    body = request(count)
    body["state"] = request(1)["state"]
    return body


def blocks_only(count):
    """The state of `count` findings with one question: the blocks' own tokens."""
    body = request(count)
    body["questions"] = {"f1": body["questions"]["f1"]}
    return body


def main():
    jev.require_key()
    rows = []
    for count in (1, 10, 50, 100, 200):
        rows.append(send("questions", request(count)))
    for count in (100, 200):
        rows.append(send("questions only", questions_only(count)))
    for count in (200, 500):
        rows.append(send("blocks only", blocks_only(count)))
    for chars in (2_000, 16_000, 32_000, 64_000):
        rows.append(send("padded state", padded(chars)))
    bisect("question ceiling", request, 400, 500, 3, rows)
    bisect("state ceiling", padded, 100_000, 150_000, 1_500, rows)
    rows.append(send("shipped, short findings", packed(600, 10)))
    rows.append(send("shipped, full state of prose", packed(600, 40, "plain words of docs ")))
    rows.append(send("shipped, full state of one letter", packed(600, 40)))
    (HERE / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
