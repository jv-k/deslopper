"""Triage: the pass that asks Jev whether each finding is a tic or a deliberate use.

Every test fakes `jev.post`. The bodies the fake records are the only view into how a
request is built, and the findings that come back are what the user sees.
"""

import pytest

from deslopper import jev, triage
from deslopper.findings import Finding, LintResult

FAKE_KEY = "test-key-not-real"


@pytest.fixture(autouse=True)
def fake_key(monkeypatch):
    monkeypatch.setenv("AI_GATEWAY_API_KEY", FAKE_KEY)


def _reply(verdicts, keys, tokens=(1577, 0), cost="0.000066"):
    """A gateway envelope answering `keys` in order from `verdicts`, cycling."""
    answers = {}
    for i, key in enumerate(keys):
        choice, probability = verdicts[i % len(verdicts)]
        answers[key] = {
            "type": "choice",
            "choice": choice,
            "probabilities": {choice: probability, _other(choice): 1 - probability},
            "confidence": probability,
        }
    return {
        "answers": answers,
        "usage": {"inputTokens": tokens[0], "outputTokens": tokens[1]},
        "providerMetadata": {"gateway": {"marketCost": cost}},
    }


def _other(choice):
    return "keep" if choice == "rewrite" else "rewrite"


def _canned(monkeypatch, verdicts, **envelope):
    """Swap the transport for one that answers every question from `verdicts`."""
    calls = []

    def post(body):
        calls.append(body)
        return _reply(verdicts, list(body["questions"]), **envelope)

    monkeypatch.setattr(jev, "post", post)
    return calls


def _finding(path, line, col, name, tier="warn", message="msg"):
    return Finding(path, line, col, tier, name, message)


def test_run_annotates_each_finding_with_the_verdict_and_its_probability(monkeypatch):
    _canned(monkeypatch, [("keep", 0.93), ("rewrite", 0.88)])
    result = LintResult(findings=[
        _finding("a.md", 1, 3, "em-dash", tier="error"),
        _finding("a.md", 2, 1, "semicolon"),
    ], unreadable=["gone.md"])

    judged = triage.run(result, {"a.md": "a — b\nc; d\n"})

    verdicts = [(f.verdict, f.probability) for f in judged.result.findings]
    assert verdicts == [("keep", 0.93), ("rewrite", 0.88)]
    # Everything else about a finding, and the result, is untouched.
    assert [(f.path, f.line, f.col, f.tier, f.name) for f in judged.result.findings] == [
        ("a.md", 1, 3, "error", "em-dash"), ("a.md", 2, 1, "warn", "semicolon"),
    ]
    assert judged.result.unreadable == ["gone.md"]


def test_one_request_per_file_carries_the_framing_and_each_finding_in_raw_context(monkeypatch):
    calls = _canned(monkeypatch, [("keep", 0.9)])
    result = LintResult(findings=[
        _finding("a.md", 2, 5, "em-dash", message="em dash, prefer a comma"),
        _finding("b.md", 1, 1, "semicolon", message="semicolon in prose"),
    ])
    sources = {
        "a.md": "first line\nsee `code` — here\nlast line\n",
        "b.md": "one; two\n",
        "clean.md": "nothing flagged\n",
    }

    triage.run(result, sources)

    assert [body["model"] for body in calls] == [jev.MODEL, jev.MODEL]
    state = calls[0]["state"]
    assert state.startswith(triage.FRAMING)
    assert "em-dash" in state and "em dash, prefer a comma" in state
    # The raw line, backticks and all, with its neighbours: the editor sees raw text.
    assert "see `code` — here" in state
    assert "first line" in state and "last line" in state
    assert "nothing flagged" not in state
    # The one question is a choice between rewrite and keep, keyed like its block.
    (key, question), = calls[0]["questions"].items()
    assert f"[{key}]" in state
    assert question["type"] == "choice"
    assert set(question["criteria"]) == {"rewrite", "keep"}
    assert "one; two" in calls[1]["state"] and "em-dash" not in calls[1]["state"]


def test_context_stops_at_the_file_edges(monkeypatch):
    calls = _canned(monkeypatch, [("keep", 0.9)])
    result = LintResult(findings=[_finding("a.md", 1, 1, "semicolon")])

    triage.run(result, {"a.md": "only; line\n"})

    lines = calls[0]["state"].splitlines()
    assert lines[-1].endswith("only; line")


def test_two_findings_on_one_line_get_independent_verdicts(monkeypatch):
    calls = _canned(monkeypatch, [("rewrite", 0.8), ("keep", 0.7)])
    result = LintResult(findings=[
        _finding("a.md", 1, 3, "em-dash"),
        _finding("a.md", 1, 9, "semicolon"),
    ])

    judged = triage.run(result, {"a.md": "a — b; c\n"})

    assert len(calls[0]["questions"]) == 2
    assert [(f.verdict, f.probability) for f in judged.result.findings] == [
        ("rewrite", 0.8), ("keep", 0.7),
    ]


def test_a_result_with_no_findings_makes_no_request(monkeypatch):
    calls = _canned(monkeypatch, [("keep", 0.9)])

    judged = triage.run(LintResult(), {})

    assert calls == []
    assert judged.result.findings == []


def test_a_failed_request_leaves_that_file_unjudged_and_the_rest_continue(monkeypatch):
    calls = []

    def post(body):
        calls.append(body)
        if len(calls) == 2:
            raise jev.JevError("gateway returned 500: boom")
        return _reply([("keep", 0.9)], list(body["questions"]))

    monkeypatch.setattr(jev, "post", post)
    result = LintResult(findings=[
        _finding("a.md", 1, 1, "semicolon"),
        _finding("b.md", 1, 1, "semicolon"),
        _finding("c.md", 1, 1, "semicolon"),
    ])

    judged = triage.run(result, {"a.md": "a; b\n", "b.md": "c; d\n", "e": "", "c.md": "e; f\n"})

    assert [f.verdict for f in judged.result.findings] == ["keep", None, "keep"]
    assert len(calls) == 3
    assert judged.errors == ["b.md: gateway returned 500: boom"]


def test_tokens_and_cost_are_summed_across_requests(monkeypatch):
    _canned(monkeypatch, [("keep", 0.9)], tokens=(1000, 7), cost="0.000066")
    result = LintResult(findings=[
        _finding("a.md", 1, 1, "semicolon"),
        _finding("b.md", 1, 1, "semicolon"),
    ])

    judged = triage.run(result, {"a.md": "a; b\n", "b.md": "c; d\n"})

    assert judged.tokens == 2014
    assert judged.cost == "0.000132"
    assert judged.keep == 2 and judged.rewrite == 0


def test_a_reply_without_usage_or_cost_still_counts_the_verdicts(monkeypatch):
    def post(body):
        return {"answers": {key: {"type": "choice", "choice": "rewrite",
                                  "probabilities": {"rewrite": 0.6, "keep": 0.4}}
                            for key in body["questions"]}}

    monkeypatch.setattr(jev, "post", post)
    result = LintResult(findings=[_finding("a.md", 1, 1, "semicolon")])

    judged = triage.run(result, {"a.md": "a; b\n"})

    assert (judged.keep, judged.rewrite) == (0, 1)
    assert judged.tokens == 0
    assert judged.cost == "0"
