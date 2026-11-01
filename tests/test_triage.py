"""Triage: the pass that asks Jev whether each finding is a tic or a deliberate use.

Every test fakes `jev.post`. The bodies the fake records are the only view into how a
request is built, and the findings that come back are what the user sees.
"""

from decimal import Decimal

import pytest

from deslopper import cache, jev, triage
from deslopper.findings import Finding, LintResult
from tests.conftest import FAKE_KEY, canned_jev, jev_envelope

@pytest.fixture(autouse=True)
def fake_key(monkeypatch):
    monkeypatch.setenv(jev.KEY_VAR, FAKE_KEY)


def _finding(path, line, col, name, tier="warn", message="msg"):
    return Finding(path, line, col, tier, name, message)


def test_run_annotates_each_finding_with_the_verdict_and_its_probability(monkeypatch):
    canned_jev(monkeypatch, [("keep", 0.93), ("rewrite", 0.88)])
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


def test_one_request_carries_the_framing_and_each_finding_in_raw_context(monkeypatch):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
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

    # Both files fit under the budget, so they share one request.
    assert [body["model"] for body in calls] == [jev.MODEL]
    state = calls[0]["state"]
    assert state.startswith(triage.FRAMING)
    assert "em-dash" in state and "em dash, prefer a comma" in state
    # The raw line, backticks and all, with its neighbours: the editor sees raw text.
    assert "see `code` — here" in state
    assert "first line" in state and "last line" in state
    assert "nothing flagged" not in state
    # Each question is a choice between rewrite and keep, keyed like its block.
    assert len(calls[0]["questions"]) == 2
    for key, question in calls[0]["questions"].items():
        assert f"[{key}]" in state
        assert question["type"] == "choice"
        assert set(question["criteria"]) == {"rewrite", "keep"}
    assert "one; two" in state and state.index("em-dash") < state.index("one; two")


def test_context_stops_at_the_file_edges(monkeypatch):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    result = LintResult(findings=[_finding("a.md", 1, 1, "semicolon")])

    triage.run(result, {"a.md": "only; line\n"})

    lines = calls[0]["state"].splitlines()
    assert lines[-1].endswith("only; line")


def test_two_findings_on_one_line_get_independent_verdicts(monkeypatch):
    calls = canned_jev(monkeypatch, [("rewrite", 0.8), ("keep", 0.7)])
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
    calls = canned_jev(monkeypatch, [("keep", 0.9)])

    judged = triage.run(LintResult(), {})

    assert calls == []
    assert judged.result.findings == []


def test_a_failed_request_leaves_that_file_unjudged_and_the_rest_continue(monkeypatch):
    calls = []

    def post(body):
        calls.append(body)
        if len(calls) == 2:
            raise jev.JevError("gateway returned 500: boom")
        return jev_envelope([("keep", 0.9)], list(body["questions"]))

    monkeypatch.setattr(jev, "post", post)
    # A budget no block fits under sends each finding in a request of its own.
    monkeypatch.setattr(jev, "STATE_CHAR_BUDGET", 1)
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
    canned_jev(monkeypatch, [("keep", 0.9)], tokens=(1000, 7), cost="0.000066")
    monkeypatch.setattr(jev, "STATE_CHAR_BUDGET", 1)
    result = LintResult(findings=[
        _finding("a.md", 1, 1, "semicolon"),
        _finding("b.md", 1, 1, "semicolon"),
    ])

    judged = triage.run(result, {"a.md": "a; b\n", "b.md": "c; d\n"})

    assert judged.tokens == 2014
    assert judged.cost == Decimal("0.000132")
    assert (judged.result.keep, judged.result.rewrite) == (2, 0)


def test_a_reply_without_usage_or_cost_still_counts_the_verdicts(monkeypatch):
    def post(body):
        return {"answers": {key: {"type": "choice", "choice": "rewrite",
                                  "probabilities": {"rewrite": 0.6, "keep": 0.4}}
                            for key in body["questions"]}}

    monkeypatch.setattr(jev, "post", post)
    result = LintResult(findings=[_finding("a.md", 1, 1, "semicolon")])

    judged = triage.run(result, {"a.md": "a; b\n"})

    assert (judged.result.keep, judged.result.rewrite) == (0, 1)
    assert judged.tokens == 0
    assert judged.cost == Decimal(0)


def test_a_garbled_answer_is_reported_and_leaves_that_finding_unjudged(monkeypatch):
    def post(body):
        f1, f2, f3, f4 = body["questions"]
        return {"answers": {
            f1: {"type": "choice", "choice": "keep", "probabilities": {"keep": 0.9, "rewrite": 0.1}},
            f2: {"type": "choice", "choice": "maybe", "probabilities": {"maybe": 0.9}},
            f3: {"type": "choice", "choice": "rewrite", "probabilities": {"rewrite": 1.5}},
            # f4 is missing from the reply altogether.
        }}

    monkeypatch.setattr(jev, "post", post)
    result = LintResult(findings=[_finding("a.md", n, 1, "semicolon") for n in (1, 2, 3, 4)])

    judged = triage.run(result, {"a.md": "a; b\nc; d\ne; f\ng; h\n"})

    assert [f.verdict for f in judged.result.findings] == ["keep", None, None, None]
    assert judged.errors == ["a.md: the reply had no usable answer for 3 of 4 findings"]


# Batching: findings are packed across files into as few requests as fit under the
# client's state budget, in file order.


def _many(files=4, per_file=3):
    """`files` files of `per_file` flagged lines each, every line text unique, as the
    lint result and its sources."""
    findings, sources = [], {}
    for f in range(files):
        path = f"doc{f}.md"
        sources[path] = "".join(f"file {f} line {n}; tail\n" for n in range(1, per_file + 1))
        findings += [_finding(path, n, 1, "semicolon") for n in range(1, per_file + 1)]
    return LintResult(findings=findings), sources


def _room(result, sources, blocks):
    """A budget with room for the framing and `blocks` of the largest block in `result`."""
    largest = max(len(triage._block("f1", f, triage._lines(sources[f.path])))
                  for f in result.findings)
    return len(triage.FRAMING) + blocks * (largest + 2)


def _flagged(state):
    """The flagged lines a request's state carries, in order."""
    return [line.split(": ", 1)[1] for line in state.splitlines() if line.startswith("> ")]


def test_a_small_budget_splits_the_findings_into_requests_and_annotates_every_one(monkeypatch):
    calls = canned_jev(monkeypatch, [("rewrite", 0.8)])
    result, sources = _many()
    budget = _room(result, sources, 2)
    monkeypatch.setattr(jev, "STATE_CHAR_BUDGET", budget)

    judged = triage.run(result, sources)

    assert len(calls) > 1
    assert all(len(body["state"]) <= budget for body in calls)
    # Every finding is asked once, in file order, and each request has one question
    # per block it carries.
    asked = [line for body in calls for line in _flagged(body["state"])]
    expected = [f"file {f} line {n}; tail" for f in range(4) for n in range(1, 4)]
    assert asked == expected
    assert all(len(body["questions"]) == len(_flagged(body["state"])) for body in calls)
    # Requests pack across files: one carries the end of one file and the start of the next.
    assert any(len({line.split()[1] for line in _flagged(body["state"])}) > 1 for body in calls)
    assert [f.verdict for f in judged.result.findings] == ["rewrite"] * 12


def test_findings_from_many_files_share_one_request_under_the_default_budget(monkeypatch):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    result, sources = _many(files=5, per_file=4)

    judged = triage.run(result, sources)

    assert len(calls) == 1
    assert len(calls[0]["questions"]) == 20
    assert (judged.result.keep, judged.result.rewrite) == (20, 0)


def test_one_file_over_the_budget_is_split_across_requests(monkeypatch):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    result, sources = _many(files=1, per_file=6)
    monkeypatch.setattr(jev, "STATE_CHAR_BUDGET", _room(result, sources, 2))

    judged = triage.run(result, sources)

    assert len(calls) == 3
    assert [f.verdict for f in judged.result.findings] == ["keep"] * 6


def test_a_finding_too_big_for_the_budget_still_goes_alone_in_its_own_request(monkeypatch):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    monkeypatch.setattr(jev, "STATE_CHAR_BUDGET", 1)
    result, sources = _many(files=1, per_file=2)

    judged = triage.run(result, sources)

    assert [len(body["questions"]) for body in calls] == [1, 1]
    assert [f.verdict for f in judged.result.findings] == ["keep", "keep"]


def test_a_failed_batch_names_its_files_and_the_next_batch_still_runs(monkeypatch):
    calls = []

    def post(body):
        calls.append(body)
        if len(calls) == 1:
            raise jev.JevError("could not reach the gateway: timed out")
        return jev_envelope([("rewrite", 0.7)], list(body["questions"]), tokens=(100, 0),
                            cost="0.00001")

    monkeypatch.setattr(jev, "post", post)
    result, sources = _many(files=3, per_file=2)
    monkeypatch.setattr(jev, "STATE_CHAR_BUDGET", _room(result, sources, 3))

    judged = triage.run(result, sources)

    assert len(calls) == 2
    # The first batch held doc0.md and the first finding of doc1.md.
    assert judged.errors == ["doc0.md, doc1.md: could not reach the gateway: timed out"]
    assert [f.verdict for f in judged.result.findings] == [None] * 3 + ["rewrite"] * 3
    assert (judged.result.keep, judged.result.rewrite) == (0, 3)
    assert (judged.tokens, judged.cost) == (100, Decimal("0.00001"))


# The cache: a finding Jev answered once is not asked about again while its tell,
# its column and the lines around it stay the same.


def test_a_second_run_answers_from_the_cache_and_makes_no_request(monkeypatch, tmp_path):
    calls = canned_jev(monkeypatch, [("keep", 0.93), ("rewrite", 0.88)])
    store = cache.Store(str(tmp_path))
    result = LintResult(findings=[
        _finding("a.md", 1, 3, "em-dash"),
        _finding("a.md", 2, 1, "semicolon"),
    ])
    sources = {"a.md": "a — b\nc; d\n"}

    first = triage.run(result, sources, cache=store)
    second = triage.run(result, sources, cache=store)

    assert len(calls) == 1
    assert (first.cached, second.cached) == (0, 2)
    assert [(f.verdict, f.probability) for f in second.result.findings] == [
        ("keep", 0.93), ("rewrite", 0.88),
    ]
    # A cached answer costs nothing.
    assert (second.tokens, second.cost) == (0, Decimal(0))


def test_only_the_findings_missing_from_the_cache_are_asked(monkeypatch, tmp_path):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    store = cache.Store(str(tmp_path))
    sources = {"a.md": "a; b\n\n\nnew; line\n"}
    triage.run(LintResult(findings=[_finding("a.md", 1, 1, "semicolon")]), sources, cache=store)

    judged = triage.run(LintResult(findings=[
        _finding("a.md", 1, 1, "semicolon"),
        _finding("a.md", 4, 1, "semicolon"),
    ]), sources, cache=store)

    assert len(calls) == 2
    assert "new; line" in calls[1]["state"] and "a; b" not in calls[1]["state"]
    assert len(calls[1]["questions"]) == 1
    assert judged.cached == 1
    assert [f.verdict for f in judged.result.findings] == ["keep", "keep"]


def test_a_finding_that_moved_down_the_file_still_hits_the_cache(monkeypatch, tmp_path):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    store = cache.Store(str(tmp_path))
    triage.run(LintResult(findings=[_finding("a.md", 2, 1, "semicolon")]),
               {"a.md": "above\na; b\nbelow\n"}, cache=store)

    judged = triage.run(LintResult(findings=[_finding("a.md", 4, 1, "semicolon")]),
                        {"a.md": "new\nlines\nabove\na; b\nbelow\n"}, cache=store)

    assert len(calls) == 1
    assert judged.cached == 1


def test_a_change_to_the_context_lines_asks_again(monkeypatch, tmp_path):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    store = cache.Store(str(tmp_path))
    triage.run(LintResult(findings=[_finding("a.md", 2, 1, "semicolon")]),
               {"a.md": "above\na; b\nbelow\n"}, cache=store)

    triage.run(LintResult(findings=[_finding("a.md", 2, 1, "semicolon")]),
               {"a.md": "above\na; b\nchanged\n"}, cache=store)

    assert len(calls) == 2


def test_a_failed_or_garbled_answer_is_not_cached(monkeypatch, tmp_path):
    store = cache.Store(str(tmp_path))
    monkeypatch.setattr(jev, "post", lambda body: {"answers": {}})
    result = LintResult(findings=[_finding("a.md", 1, 1, "semicolon")])
    triage.run(result, {"a.md": "a; b\n"}, cache=store)

    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    judged = triage.run(result, {"a.md": "a; b\n"}, cache=store)

    assert len(calls) == 1
    assert judged.cached == 0


def test_a_finding_without_source_text_is_never_cached(monkeypatch, tmp_path):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    store = cache.Store(str(tmp_path))
    result = LintResult(findings=[_finding("gone.md", 1, 1, "semicolon")])

    triage.run(result, {"gone.md": ""}, cache=store)
    triage.run(result, {"gone.md": ""}, cache=store)

    assert len(calls) == 2


# What the cache saved: each stored verdict keeps its share of the request that
# answered it, and a hit adds that share back up.


def test_a_cached_answer_counts_its_share_of_the_request_as_saved(monkeypatch, tmp_path):
    canned_jev(monkeypatch, [("keep", 0.93), ("rewrite", 0.88)],
               tokens=(1577, 0), cost="0.000066")
    store = cache.Store(str(tmp_path))
    result = LintResult(findings=[
        _finding("a.md", 1, 3, "em-dash"),
        _finding("a.md", 2, 1, "semicolon"),
    ])
    sources = {"a.md": "a — b\nc; d\n"}

    first = triage.run(result, sources, cache=store)
    second = triage.run(result, sources, cache=store)

    assert (first.saved_tokens, first.saved_cost) == (0, Decimal(0))
    # The shares add up to what the first run spent.
    assert (second.saved_tokens, second.saved_cost) == (1577, Decimal("0.000066"))


def test_an_entry_without_a_recorded_share_saves_nothing_it_can_count(monkeypatch, tmp_path):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    store = cache.Store(str(tmp_path))
    finding = _finding("a.md", 1, 1, "semicolon")
    lines = ["a; b"]
    store.put(triage._cache_key(finding, lines), {"verdict": "keep", "probability": 0.9})

    judged = triage.run(LintResult(findings=[finding]), {"a.md": "a; b\n"}, cache=store)

    assert calls == []
    assert judged.cached == 1
    assert (judged.saved_tokens, judged.saved_cost) == (0, Decimal(0))
