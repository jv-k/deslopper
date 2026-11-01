"""Triage: the pass that asks Jev whether each smell is a tic or a deliberate use.

Every test fakes `jev.post`. The bodies the fake records are the only view into how a
request is built, and the smells that come back are what the user sees.
"""

import json
from decimal import Decimal

import pytest

from deslopper import cache, jev, triage
from deslopper.smells import Smell, LintResult
from tests.conftest import FAKE_KEY, canned_jev, jev_envelope

@pytest.fixture(autouse=True)
def fake_key(monkeypatch):
    monkeypatch.setenv(jev.KEY_VAR, FAKE_KEY)


def _smell(path, line, col, name, tier="warn", message="msg"):
    return Smell(path, line, col, tier, name, message)


def test_run_annotates_each_smell_with_the_verdict_and_its_probability(monkeypatch):
    canned_jev(monkeypatch, [("keep", 0.93), ("rewrite", 0.88)])
    result = LintResult(smells=[
        _smell("a.md", 1, 3, "em-dash", tier="error"),
        _smell("a.md", 2, 1, "semicolon"),
    ], unreadable=["gone.md"])

    judged = triage.run(result, {"a.md": "a — b\nc; d\n"})

    verdicts = [(f.verdict, f.probability) for f in judged.result.smells]
    assert verdicts == [("keep", 0.93), ("rewrite", 0.88)]
    # Everything else about a smell, and the result, is untouched.
    assert [(f.path, f.line, f.col, f.tier, f.name) for f in judged.result.smells] == [
        ("a.md", 1, 3, "error", "em-dash"), ("a.md", 2, 1, "warn", "semicolon"),
    ]
    assert judged.result.unreadable == ["gone.md"]


def test_one_request_carries_the_framing_and_each_smell_in_raw_context(monkeypatch):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    result = LintResult(smells=[
        _smell("a.md", 2, 5, "em-dash", message="em dash, prefer a comma"),
        _smell("b.md", 1, 1, "semicolon", message="semicolon in prose"),
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
    result = LintResult(smells=[_smell("a.md", 1, 1, "semicolon")])

    triage.run(result, {"a.md": "only; line\n"})

    lines = calls[0]["state"].splitlines()
    assert lines[-1].endswith("only; line")


def test_two_smells_on_one_line_get_independent_verdicts(monkeypatch):
    calls = canned_jev(monkeypatch, [("rewrite", 0.8), ("keep", 0.7)])
    result = LintResult(smells=[
        _smell("a.md", 1, 3, "em-dash"),
        _smell("a.md", 1, 9, "semicolon"),
    ])

    judged = triage.run(result, {"a.md": "a — b; c\n"})

    assert len(calls[0]["questions"]) == 2
    assert [(f.verdict, f.probability) for f in judged.result.smells] == [
        ("rewrite", 0.8), ("keep", 0.7),
    ]


def test_a_result_with_no_smells_makes_no_request(monkeypatch):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])

    judged = triage.run(LintResult(), {})

    assert calls == []
    assert judged.result.smells == []


def test_a_failed_request_leaves_that_file_unjudged_and_the_rest_continue(monkeypatch):
    calls = []

    def post(body):
        calls.append(body)
        if len(calls) == 2:
            raise jev.JevError("gateway returned 500: boom")
        return jev_envelope([("keep", 0.9)], list(body["questions"]))

    monkeypatch.setattr(jev, "post", post)
    # A budget no block fits under sends each smell in a request of its own.
    monkeypatch.setattr(jev, "STATE_CHAR_BUDGET", 1)
    result = LintResult(smells=[
        _smell("a.md", 1, 1, "semicolon"),
        _smell("b.md", 1, 1, "semicolon"),
        _smell("c.md", 1, 1, "semicolon"),
    ])

    judged = triage.run(result, {"a.md": "a; b\n", "b.md": "c; d\n", "e": "", "c.md": "e; f\n"})

    assert [f.verdict for f in judged.result.smells] == ["keep", None, "keep"]
    assert len(calls) == 3
    assert judged.errors == ["b.md: gateway returned 500: boom"]


def test_tokens_and_cost_are_summed_across_requests(monkeypatch):
    canned_jev(monkeypatch, [("keep", 0.9)], tokens=(1000, 7), cost="0.000066")
    monkeypatch.setattr(jev, "STATE_CHAR_BUDGET", 1)
    result = LintResult(smells=[
        _smell("a.md", 1, 1, "semicolon"),
        _smell("b.md", 1, 1, "semicolon"),
    ])

    judged = triage.run(result, {"a.md": "a; b\n", "b.md": "c; d\n"})

    assert judged.tokens == 2014
    assert judged.cost == Decimal("0.000132")
    assert (judged.result.keep, judged.result.rewrite) == (2, 0)


def test_a_zero_cost_keeps_the_digits_the_gateway_sent(monkeypatch):
    canned_jev(monkeypatch, [("keep", 0.9)], tokens=(10, 1), cost="0.000000")
    result = LintResult(smells=[_smell("a.md", 1, 1, "semicolon")])

    judged = triage.run(result, {"a.md": "a; b\n"})

    assert f"{judged.cost:f}" == "0.000000"


def test_a_reply_without_usage_or_cost_still_counts_the_verdicts(monkeypatch):
    def post(body):
        return {"answers": {key: {"type": "choice", "choice": "rewrite",
                                  "probabilities": {"rewrite": 0.6, "keep": 0.4}}
                            for key in body["questions"]}}

    monkeypatch.setattr(jev, "post", post)
    result = LintResult(smells=[_smell("a.md", 1, 1, "semicolon")])

    judged = triage.run(result, {"a.md": "a; b\n"})

    assert (judged.result.keep, judged.result.rewrite) == (0, 1)
    assert judged.tokens == 0
    assert judged.cost == Decimal(0)


def test_a_garbled_answer_is_reported_and_leaves_that_smell_unjudged(monkeypatch):
    def post(body):
        f1, f2, f3, f4 = body["questions"]
        return {"answers": {
            f1: {"type": "choice", "choice": "keep", "probabilities": {"keep": 0.9, "rewrite": 0.1}},
            f2: {"type": "choice", "choice": "maybe", "probabilities": {"maybe": 0.9}},
            f3: {"type": "choice", "choice": "rewrite", "probabilities": {"rewrite": 1.5}},
            # f4 is missing from the reply altogether.
        }}

    monkeypatch.setattr(jev, "post", post)
    result = LintResult(smells=[_smell("a.md", n, 1, "semicolon") for n in (1, 2, 3, 4)])

    judged = triage.run(result, {"a.md": "a; b\nc; d\ne; f\ng; h\n"})

    assert [f.verdict for f in judged.result.smells] == ["keep", None, None, None]
    assert judged.errors == ["a.md: the reply had no usable answer for 3 of 4 smells"]


# Batching: smells are packed across files into as few requests as fit under the
# client's state budget, in file order.


def _many_files(files=4, per_file=3):
    """`files` files of `per_file` flagged lines each, every line text unique, as the
    lint result and its sources."""
    smells, sources = [], {}
    for f in range(files):
        path = f"doc{f}.md"
        sources[path] = "".join(f"file {f} line {n}; tail\n" for n in range(1, per_file + 1))
        smells += [_smell(path, n, 1, "semicolon") for n in range(1, per_file + 1)]
    return LintResult(smells=smells), sources


def _budget_for(result, sources, blocks):
    """A budget with room for the framing and `blocks` of the largest block in `result`."""
    largest = max(len(triage._block("f1", f, triage._lines(sources[f.path])))
                  for f in result.smells)
    return len(triage.FRAMING) + blocks * (largest + 2)


def _flagged_lines(state):
    """The flagged lines a request's state carries, in order."""
    return [line.split(": ", 1)[1] for line in state.splitlines() if line.startswith("> ")]


def test_a_small_budget_splits_the_smells_into_requests_and_annotates_every_one(monkeypatch):
    calls = canned_jev(monkeypatch, [("rewrite", 0.8)])
    result, sources = _many_files()
    budget = _budget_for(result, sources, 2)
    monkeypatch.setattr(jev, "STATE_CHAR_BUDGET", budget)

    judged = triage.run(result, sources)

    assert len(calls) > 1
    assert all(len(body["state"]) <= budget for body in calls)
    # Every smell is asked once, in file order, and each request has one question
    # per block it carries.
    asked = [line for body in calls for line in _flagged_lines(body["state"])]
    expected = [f"file {f} line {n}; tail" for f in range(4) for n in range(1, 4)]
    assert asked == expected
    assert all(len(body["questions"]) == len(_flagged_lines(body["state"])) for body in calls)
    # Requests pack across files: one carries the end of one file and the start of the next.
    assert any(len({line.split()[1] for line in _flagged_lines(body["state"])}) > 1 for body in calls)
    assert [f.verdict for f in judged.result.smells] == ["rewrite"] * 12


def test_smells_from_many_files_share_one_request_under_the_default_budget(monkeypatch):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    result, sources = _many_files(files=5, per_file=4)

    judged = triage.run(result, sources)

    assert len(calls) == 1
    assert len(calls[0]["questions"]) == 20
    assert (judged.result.keep, judged.result.rewrite) == (20, 0)


def test_one_file_over_the_budget_is_split_across_requests(monkeypatch):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    result, sources = _many_files(files=1, per_file=6)
    monkeypatch.setattr(jev, "STATE_CHAR_BUDGET", _budget_for(result, sources, 2))

    judged = triage.run(result, sources)

    assert len(calls) == 3
    assert [f.verdict for f in judged.result.smells] == ["keep"] * 6


def test_many_short_smells_split_on_the_question_budget_before_the_state_budget(monkeypatch):
    # 600 short smells make about 80,000 characters of state, so the state budget
    # alone would put 478 questions in the first request. Jev refused 418 in the
    # measurement, so the questions must close each batch first.
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    result, sources = _many_files(files=1, per_file=600)

    judged = triage.run(result, sources)

    question_chars = [len(json.dumps(body["questions"])) for body in calls]
    assert len(calls) > 2
    assert all(size <= jev.QUESTION_CHAR_BUDGET for size in question_chars)
    # Each full batch closed on its questions, far short of the state budget.
    assert all(len(body["state"]) < 0.6 * jev.STATE_CHAR_BUDGET for body in calls)
    one_question = question_chars[-1] / len(calls[-1]["questions"])
    assert all(size + one_question > jev.QUESTION_CHAR_BUDGET for size in question_chars[:-1])
    assert sum(len(body["questions"]) for body in calls) == 600
    assert judged.result.keep == 600


def test_a_question_over_the_question_budget_still_goes_alone_in_its_own_request(monkeypatch):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    monkeypatch.setattr(jev, "QUESTION_CHAR_BUDGET", 1)
    result, sources = _many_files(files=1, per_file=2)

    judged = triage.run(result, sources)

    assert [len(body["questions"]) for body in calls] == [1, 1]
    assert [f.verdict for f in judged.result.smells] == ["keep", "keep"]


def test_a_smell_too_big_for_the_budget_still_goes_alone_in_its_own_request(monkeypatch):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    monkeypatch.setattr(jev, "STATE_CHAR_BUDGET", 1)
    result, sources = _many_files(files=1, per_file=2)

    judged = triage.run(result, sources)

    assert [len(body["questions"]) for body in calls] == [1, 1]
    assert [f.verdict for f in judged.result.smells] == ["keep", "keep"]


def test_a_failed_batch_names_its_files_and_the_next_batch_still_runs(monkeypatch):
    calls = []

    def post(body):
        calls.append(body)
        if len(calls) == 1:
            raise jev.JevError("could not reach the gateway: timed out")
        return jev_envelope([("rewrite", 0.7)], list(body["questions"]), tokens=(100, 0),
                            cost="0.00001")

    monkeypatch.setattr(jev, "post", post)
    result, sources = _many_files(files=3, per_file=2)
    monkeypatch.setattr(jev, "STATE_CHAR_BUDGET", _budget_for(result, sources, 3))

    judged = triage.run(result, sources)

    assert len(calls) == 2
    # The first batch held doc0.md and the first smell of doc1.md.
    assert judged.errors == ["doc0.md, doc1.md: could not reach the gateway: timed out"]
    assert [f.verdict for f in judged.result.smells] == [None] * 3 + ["rewrite"] * 3
    assert (judged.result.keep, judged.result.rewrite) == (0, 3)
    assert (judged.tokens, judged.cost) == (100, Decimal("0.00001"))


def test_a_failed_batch_of_many_files_names_the_first_few_and_counts_the_rest(monkeypatch):
    def post(body):
        raise jev.JevError("gateway returned 500: boom")

    monkeypatch.setattr(jev, "post", post)
    result, sources = _many_files(files=5, per_file=1)

    judged = triage.run(result, sources)

    assert judged.errors == ["doc0.md, doc1.md, doc2.md and 2 more files: gateway returned 500: boom"]


# The cache: a smell Jev answered once is not asked about again while its tell,
# its column and the lines around it stay the same.


def test_a_second_run_answers_from_the_cache_and_makes_no_request(monkeypatch, tmp_path):
    calls = canned_jev(monkeypatch, [("keep", 0.93), ("rewrite", 0.88)])
    store = cache.Store(str(tmp_path))
    result = LintResult(smells=[
        _smell("a.md", 1, 3, "em-dash"),
        _smell("a.md", 2, 1, "semicolon"),
    ])
    sources = {"a.md": "a — b\nc; d\n"}

    first = triage.run(result, sources, cache=store)
    second = triage.run(result, sources, cache=store)

    assert len(calls) == 1
    assert (first.cached, second.cached) == (0, 2)
    assert [(f.verdict, f.probability) for f in second.result.smells] == [
        ("keep", 0.93), ("rewrite", 0.88),
    ]
    # A cached answer costs nothing.
    assert (second.tokens, second.cost) == (0, Decimal(0))


def test_only_the_smells_missing_from_the_cache_are_asked(monkeypatch, tmp_path):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    store = cache.Store(str(tmp_path))
    sources = {"a.md": "a; b\n\n\nnew; line\n"}
    triage.run(LintResult(smells=[_smell("a.md", 1, 1, "semicolon")]), sources, cache=store)

    judged = triage.run(LintResult(smells=[
        _smell("a.md", 1, 1, "semicolon"),
        _smell("a.md", 4, 1, "semicolon"),
    ]), sources, cache=store)

    assert len(calls) == 2
    assert "new; line" in calls[1]["state"] and "a; b" not in calls[1]["state"]
    assert len(calls[1]["questions"]) == 1
    assert judged.cached == 1
    assert [f.verdict for f in judged.result.smells] == ["keep", "keep"]


def test_a_smell_that_moved_down_the_file_still_hits_the_cache(monkeypatch, tmp_path):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    store = cache.Store(str(tmp_path))
    triage.run(LintResult(smells=[_smell("a.md", 2, 1, "semicolon")]),
               {"a.md": "above\na; b\nbelow\n"}, cache=store)

    judged = triage.run(LintResult(smells=[_smell("a.md", 4, 1, "semicolon")]),
                        {"a.md": "new\nlines\nabove\na; b\nbelow\n"}, cache=store)

    assert len(calls) == 1
    assert judged.cached == 1


def test_a_change_to_the_context_lines_asks_again(monkeypatch, tmp_path):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    store = cache.Store(str(tmp_path))
    triage.run(LintResult(smells=[_smell("a.md", 2, 1, "semicolon")]),
               {"a.md": "above\na; b\nbelow\n"}, cache=store)

    triage.run(LintResult(smells=[_smell("a.md", 2, 1, "semicolon")]),
               {"a.md": "above\na; b\nchanged\n"}, cache=store)

    assert len(calls) == 2


def test_a_failed_or_garbled_answer_is_not_cached(monkeypatch, tmp_path):
    store = cache.Store(str(tmp_path))
    monkeypatch.setattr(jev, "post", lambda body: {"answers": {}})
    result = LintResult(smells=[_smell("a.md", 1, 1, "semicolon")])
    triage.run(result, {"a.md": "a; b\n"}, cache=store)

    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    judged = triage.run(result, {"a.md": "a; b\n"}, cache=store)

    assert len(calls) == 1
    assert judged.cached == 0


def test_a_smell_without_source_text_is_never_cached(monkeypatch, tmp_path):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    store = cache.Store(str(tmp_path))
    result = LintResult(smells=[_smell("gone.md", 1, 1, "semicolon")])

    triage.run(result, {"gone.md": ""}, cache=store)
    triage.run(result, {"gone.md": ""}, cache=store)

    assert len(calls) == 2


# What the cache saved: each stored verdict keeps its share of the request that
# answered it, and a hit adds that share back up.


def test_a_cached_answer_counts_its_share_of_the_request_as_saved(monkeypatch, tmp_path):
    canned_jev(monkeypatch, [("keep", 0.93), ("rewrite", 0.88)],
               tokens=(1577, 0), cost="0.000066")
    store = cache.Store(str(tmp_path))
    result = LintResult(smells=[
        _smell("a.md", 1, 3, "em-dash"),
        _smell("a.md", 2, 1, "semicolon"),
    ])
    sources = {"a.md": "a — b\nc; d\n"}

    first = triage.run(result, sources, cache=store)
    second = triage.run(result, sources, cache=store)

    assert (first.saved_tokens, first.saved_cost) == (0, Decimal(0))
    # The shares add up to what the first run spent.
    assert (second.saved_tokens, second.saved_cost) == (1577, Decimal("0.000066"))


@pytest.mark.parametrize(
    "cost, saved",
    [
        ("0.000066", Decimal("0.000066")),
        ("6.6E-5", Decimal("0.000066")),
        (6.6e-05, Decimal("0.000066")),
        # What `run` caches for a request that cost nothing: the zero keeps its places.
        ("0.000000000", Decimal("0.000000000")),
        (None, Decimal(0)),
        ("not a number", Decimal(0)),
        ("-0.5", Decimal(0)),
        ("NaN", Decimal(0)),
        ("Infinity", Decimal(0)),
    ],
    ids=["plain", "exponent-form", "unquoted-number", "zero", "missing", "garbage",
         "negative", "nan", "infinity"],
)
def test_a_cached_cost_reads_as_its_decimal_or_zero(cost, saved, monkeypatch, tmp_path):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    store = cache.Store(str(tmp_path))
    smell = _smell("a.md", 1, 1, "semicolon")
    store.put(triage._cache_key(smell, ["a; b"]),
              {"verdict": "keep", "probability": 0.9, "tokens": 5, "cost": cost})

    judged = triage.run(LintResult(smells=[smell]), {"a.md": "a; b\n"}, cache=store)

    assert calls == []
    # Compared as printed, since the report prints the saved cost with `:f`.
    assert f"{judged.saved_cost:f}" == f"{saved:f}"
    assert isinstance(judged.saved_cost, Decimal)


def test_an_entry_without_a_recorded_share_saves_nothing_it_can_count(monkeypatch, tmp_path):
    calls = canned_jev(monkeypatch, [("keep", 0.9)])
    store = cache.Store(str(tmp_path))
    smell = _smell("a.md", 1, 1, "semicolon")
    lines = ["a; b"]
    store.put(triage._cache_key(smell, lines), {"verdict": "keep", "probability": 0.9})

    judged = triage.run(LintResult(smells=[smell]), {"a.md": "a; b\n"}, cache=store)

    assert calls == []
    assert judged.cached == 1
    assert (judged.saved_tokens, judged.saved_cost) == (0, Decimal(0))
