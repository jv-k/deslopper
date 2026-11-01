"""Measure how the questions in a triage request use Jev's window (issue #87).

Run from the repo root with the gateway key exported. Each request costs a fraction
of a cent:

    .venv/bin/python docs/qa/jev-question-budget-87/probe.py

It sends real triage requests, built by `triage._block`, `triage._state` and the
triage question, and records for each one the characters of state, the characters
of the questions as JSON, the input and output tokens the gateway reports, the
seconds the request took, and on a refusal the reason the provider gave. The
sweeps grow the question count on short smells, then the questions alone, then
the smells' blocks alone, then one padded line of state, so the tokens per
character of each part can be read off. Two bisections then find the largest
request the gateway accepts: one by question count on short smells, one by the
length of a state with one question. The check at the end packs smells with
`triage._batches` and sends the first, fullest batch: once for short smells under
the state budget alone, as triage packed them before issue #87, then under the
shipped budgets, once for short smells and twice for smells sized to fill both
budgets together. It reads triage's private helpers on purpose, so the requests
are the ones triage builds. Results go to `results.json` beside this file.
"""
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from deslopper import jev, triage
from deslopper.smells import Smell

HERE = Path(__file__).resolve().parent
SMELL = Smell("a.md", 1, 1, "warn", "semicolon", "semicolon in prose, use a full stop")


def request(count, line="a short flagged line; tail"):
    """A triage request of `count` short smells, as `triage.run` builds it."""
    blocks, questions = [], {}
    for i in range(1, count + 1):
        key = f"f{i}"
        blocks.append(triage._block(key, SMELL, [f"{i} {line}"]))
        questions[key] = jev.choice(
            triage.QUESTION.format(key=key, name=SMELL.name, line=1, col=1), triage.OPTIONS)
    return {"model": jev.MODEL, "state": triage._state(blocks), "questions": questions}


def padded(state_chars):
    """One smell whose flagged line is padded so the state is `state_chars` long."""
    body = request(1)
    extra = max(state_chars - len(body["state"]), 0)
    words = ("plain words in a long line of docs " * (extra // 35 + 1))[:extra]
    return request(1, line="a short flagged line; " + words)


def packed(count, width, fill="w", question_budget=None):
    """The first batch `triage._batches` packs from `count` smells in one file,
    each flagged line about `width` characters long, under the shipped budgets, or
    under `question_budget` characters of questions when it is given. A
    fill of one repeated letter is the densest state per token the probe found;
    a fill of words is closer to prose."""
    pad = (fill * width)[:width]
    text = "".join(f"{n:05d} {pad}; tail\n" for n in range(1, count + 1))
    lines = triage._lines(text)
    smells = [Smell("a.md", n, 1, "warn", SMELL.name, SMELL.message) for n in range(1, count + 1)]
    pending = [triage.Pending(i, None, lines) for i in range(count)]
    if question_budget is None:
        question_budget = jev.QUESTION_CHAR_BUDGET
    batch = triage._batches(smells, pending, jev.STATE_CHAR_BUDGET, question_budget)[0]
    return {"model": jev.MODEL, "state": triage._state([e.block for e in batch.values()]),
            "questions": {key: e.question for key, e in batch.items()}}


def send(label, body):
    row = {"label": label, "questions": len(body["questions"]),
           "state_chars": len(body["state"]),
           "question_chars": len(json.dumps(body["questions"]))}
    request = urllib.request.Request(
        jev.ENDPOINT, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {jev.require_key()}",
                 "Content-Type": "application/json"})
    start = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            reply = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        row["seconds"] = round(time.monotonic() - start, 2)
        text = err.read().decode("utf-8", "replace")
        # The provider's reason sits in the gateway's routing record, escaped.
        reason = re.search(r'error_type\\*":\\*"([a-z_]+)', text)
        row["error"] = f"{err.code} {reason.group(1) if reason else 'no reason given'}"
    else:
        row["seconds"] = round(time.monotonic() - start, 2)
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
    """`count` questions about the state of one smell: the questions' own tokens."""
    body = request(count)
    body["state"] = request(1)["state"]
    return body


def blocks_only(count):
    """The state of `count` smells with one question: the blocks' own tokens."""
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
    rows.append(send("state budget alone, short smells", packed(600, 10, question_budget=10**9)))
    rows.append(send("shipped, short smells", packed(600, 10)))
    rows.append(send("shipped, full state of prose", packed(600, 40, "plain words of docs ")))
    rows.append(send("shipped, full state of one letter", packed(600, 40)))
    (HERE / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
