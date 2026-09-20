"""The Jev client: question builders, the evaluate entry point, and the transport.

Every test fakes the network. `evaluate` is tested with `jev.post` swapped for a
canned answer; `post` itself is tested with `urllib.request.urlopen` swapped out.
No test needs AI_GATEWAY_API_KEY set, and none prints the fake key on failure.
"""

import io
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

import pytest

from deslopper import jev

FAKE_KEY = "test-key-not-real"

# The three answer shapes captured from a live probe on 2026-09-20 (#31), one of
# each type, under one response envelope.
PROBE_RESPONSE = {
    "answers": {
        "tic": {"type": "boolean", "probability": 0.94},
        "edit": {
            "type": "choice",
            "choice": "light",
            "probabilities": {"rewrite": 0.35, "none": 0.15, "light": 0.5},
            "confidence": 0.24,
        },
        "plain": {
            "type": "score",
            "score": 0.01,
            "probabilities": {"0": 0.99, "1": 0.01, "2": 0},
            "confidence": 0.98,
        },
    },
    "usage": {"inputTokens": 1577, "outputTokens": 0},
    "providerMetadata": {
        "typesafe": {"confidence": {"tic": 0.88, "edit": 0.24, "plain": 0.98}},
        "gateway": {"marketCost": "0.000066"},
    },
}

QUESTIONS = {
    "tic": jev.boolean("A tic?", true="tic", false="choice"),
    "edit": jev.choice("How much?", {"none": "n", "light": "l", "rewrite": "r"}),
    "plain": jev.score("Plain?", ["slop", "mixed", "plain"]),
}

BODY = {"model": jev.MODEL, "state": "s", "questions": QUESTIONS}


@pytest.fixture(autouse=True)
def fake_key(monkeypatch):
    """Every test starts with a fake key exported; the no-key tests remove it."""
    monkeypatch.setenv("AI_GATEWAY_API_KEY", FAKE_KEY)


def _canned(response):
    """A fake transport that records the body it was handed and returns response."""
    calls = []

    def post(body):
        calls.append(body)
        return response

    post.calls = calls
    return post


class _Reply:
    """What a faked urlopen hands back: a context manager with a read()."""

    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self.payload


def _fake_urlopen(monkeypatch, outcome):
    """Swap urlopen for one that records the Request and returns or raises outcome."""
    seen = {}

    def urlopen(request, timeout=None):
        seen["request"] = request
        seen["timeout"] = timeout
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    return seen


def _http_error(status: int, body: dict):
    payload = json.dumps(body).encode()
    return urllib.error.HTTPError(jev.ENDPOINT, status, "nope", {}, io.BytesIO(payload))


# Builders


def test_boolean_builder_emits_the_true_false_criteria_object():
    q = jev.boolean("Is the line a machine tic?", true="a tic", false="a human choice")
    assert q == {
        "type": "boolean",
        "instructions": "Is the line a machine tic?",
        "criteria": {"true": "a tic", "false": "a human choice"},
    }


def test_choice_builder_emits_an_option_to_description_object():
    q = jev.choice("How much rewriting?", {"none": "leave it", "light": "a word", "rewrite": "the line"})
    assert q == {
        "type": "choice",
        "instructions": "How much rewriting?",
        "criteria": {"none": "leave it", "light": "a word", "rewrite": "the line"},
    }


def test_score_builder_emits_an_array_of_bucket_labels():
    q = jev.score("How plain is it?", ["slop", "mixed", "plain"])
    assert q == {
        "type": "score",
        "instructions": "How plain is it?",
        "criteria": ["slop", "mixed", "plain"],
    }


# evaluate, with post faked


def test_evaluate_posts_the_pinned_model_with_state_and_questions_untouched(monkeypatch):
    post = _canned(PROBE_RESPONSE)
    monkeypatch.setattr(jev, "post", post)

    jev.evaluate("line 1: Furthermore, it is worth noting.", QUESTIONS)

    assert post.calls == [
        {
            "model": "typesafe-ai/jev",
            "state": "line 1: Furthermore, it is worth noting.",
            "questions": QUESTIONS,
        }
    ]
    assert jev.MODEL == "typesafe-ai/jev"
    assert jev.ENDPOINT == "https://ai-gateway.vercel.sh/v1/evaluate"


def test_evaluate_parses_the_captured_answers_usage_and_cost(monkeypatch):
    monkeypatch.setattr(jev, "post", _canned(PROBE_RESPONSE))

    result = jev.evaluate("some state", QUESTIONS)

    tic = result.answers["tic"]
    assert (tic.kind, tic.value) == ("boolean", 0.94)
    assert tic.probabilities == pytest.approx({"true": 0.94, "false": 0.06})
    assert tic.confidence == 0.88

    edit = result.answers["edit"]
    assert (edit.kind, edit.value) == ("choice", "light")
    assert edit.probabilities == {"rewrite": 0.35, "none": 0.15, "light": 0.5}
    assert edit.confidence == 0.24

    plain = result.answers["plain"]
    assert (plain.kind, plain.value) == ("score", 0.01)
    assert plain.probabilities == {"0": 0.99, "1": 0.01, "2": 0}
    assert plain.confidence == 0.98

    assert (result.input_tokens, result.output_tokens) == (1577, 0)
    assert result.market_cost == "0.000066"


def test_an_answer_of_unknown_type_raises_jev_error(monkeypatch):
    reply = {"answers": {"tic": {"type": "ranking", "order": ["a", "b"]}}}
    monkeypatch.setattr(jev, "post", _canned(reply))

    with pytest.raises(jev.JevError) as excinfo:
        jev.evaluate("some state", QUESTIONS)

    assert "ranking" in str(excinfo.value)


def test_missing_key_raises_unavailable_naming_the_variable_and_never_posts(monkeypatch):
    monkeypatch.delenv("AI_GATEWAY_API_KEY")
    post = _canned(PROBE_RESPONSE)
    monkeypatch.setattr(jev, "post", post)

    with pytest.raises(jev.JevUnavailable) as excinfo:
        jev.evaluate("some state", QUESTIONS)

    assert "AI_GATEWAY_API_KEY" in str(excinfo.value)
    assert post.calls == []


@pytest.mark.parametrize("state, questions", [("", QUESTIONS), ("some state", {})])
def test_empty_state_or_questions_raises_before_any_call(monkeypatch, state, questions):
    post = _canned(PROBE_RESPONSE)
    monkeypatch.setattr(jev, "post", post)

    with pytest.raises(ValueError):
        jev.evaluate(state, questions)

    assert post.calls == []


class _SpyEnviron(dict):
    """A stand-in for os.environ that records every name looked up, however."""

    def __init__(self, source):
        super().__init__(source)
        self.read = []

    def __getitem__(self, name):
        self.read.append(name)
        return super().__getitem__(name)

    def get(self, name, default=None):
        self.read.append(name)
        return super().get(name, default)

    def __contains__(self, name):
        self.read.append(name)
        return super().__contains__(name)


def test_evaluate_reads_only_the_gateway_key_and_only_at_call_time(monkeypatch):
    """The module is already imported; the key appears now, and nothing else is
    read anywhere on the path, the real transport's header included."""
    _fake_urlopen(monkeypatch, _Reply(json.dumps(PROBE_RESPONSE).encode()))
    spy = _SpyEnviron({k: v for k, v in os.environ.items() if k != "AI_GATEWAY_API_KEY"})
    monkeypatch.setattr(os, "environ", spy)
    spy["AI_GATEWAY_API_KEY"] = FAKE_KEY

    jev.evaluate("some state", QUESTIONS)

    assert set(spy.read) == {"AI_GATEWAY_API_KEY"}


# post, with urlopen faked


def test_post_sends_a_bearer_request_to_the_endpoint_with_the_timeout(monkeypatch):
    seen = _fake_urlopen(monkeypatch, _Reply(json.dumps(PROBE_RESPONSE).encode()))

    reply = jev.post(BODY)

    request = seen["request"]
    assert request.full_url == jev.ENDPOINT
    assert request.get_method() == "POST"
    assert json.loads(request.data) == BODY
    # A boolean, so a failure prints `assert False` and never the header.
    header_is_bearer_key = request.get_header("Authorization") == "Bearer " + FAKE_KEY
    assert header_is_bearer_key
    assert seen["timeout"] == jev.TIMEOUT_SECONDS == 10
    assert reply == PROBE_RESPONSE


def test_free_tier_403_gets_the_top_up_hint(monkeypatch):
    body = {"error": {"message": "This model is not available on the free tier."}}
    _fake_urlopen(monkeypatch, _http_error(403, body))

    with pytest.raises(jev.JevError) as excinfo:
        jev.post(BODY)

    assert "top up gateway credits, the key is fine" in str(excinfo.value)


def test_other_http_errors_carry_the_gateway_message(monkeypatch):
    body = {"error": {"message": "questions.tic.criteria is required"}}
    _fake_urlopen(monkeypatch, _http_error(400, body))

    with pytest.raises(jev.JevError) as excinfo:
        jev.post(BODY)

    assert "questions.tic.criteria is required" in str(excinfo.value)
    assert "400" in str(excinfo.value)


def test_a_plain_string_error_field_is_carried_too(monkeypatch):
    """The gateway's allowlist refusals put the message straight under `error`."""
    body = {"error": "Your team has restricted access to this model.", "statusCode": 403}
    _fake_urlopen(monkeypatch, _http_error(403, body))

    with pytest.raises(jev.JevError) as excinfo:
        jev.post(BODY)

    assert "restricted access to this model" in str(excinfo.value)
    assert "top up" not in str(excinfo.value)


@pytest.mark.parametrize("payload", [b"<html>gateway timeout</html>", b'["not", "an", "object"]'])
def test_a_reply_that_is_not_a_json_object_raises_jev_error(monkeypatch, payload):
    _fake_urlopen(monkeypatch, _Reply(payload))

    with pytest.raises(jev.JevError):
        jev.post(BODY)


def test_a_stalled_gateway_raises_jev_error_not_a_bare_urlerror(monkeypatch):
    _fake_urlopen(monkeypatch, urllib.error.URLError("timed out"))

    with pytest.raises(jev.JevError) as excinfo:
        jev.post(BODY)

    assert "timed out" in str(excinfo.value)


def test_the_key_never_appears_in_an_error_message(monkeypatch):
    _fake_urlopen(monkeypatch, _http_error(500, {"error": {"message": "boom"}}))

    with pytest.raises(jev.JevError) as excinfo:
        jev.post(BODY)

    # A boolean, so a failure prints `assert False` and never the key.
    leaked = FAKE_KEY in str(excinfo.value) or FAKE_KEY in repr(excinfo.value)
    assert not leaked


def test_module_imports_cleanly_with_no_key_set():
    env = {k: v for k, v in os.environ.items() if k != "AI_GATEWAY_API_KEY"}
    proc = subprocess.run(
        [sys.executable, "-c", "import deslopper.jev as j; print(j.STATE_CHAR_BUDGET > 0)"],
        env=env, capture_output=True, text=True,
    )
    assert (proc.returncode, proc.stdout.strip()) == (0, "True"), proc.stderr
