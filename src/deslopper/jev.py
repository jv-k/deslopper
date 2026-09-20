"""The Jev client: typed questions to typesafe-ai/jev over the Vercel AI Gateway.

Consumers build questions with `boolean`, `choice`, or `score`, then call
`evaluate(state, questions)`. Every request goes through the one transport
function `post`, which tests replace with canned answers. Nothing here runs at
import time, so `deslopper lint` stays network-free on a machine with no key.
"""

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

ENDPOINT = "https://ai-gateway.vercel.sh/v1/evaluate"
MODEL = "typesafe-ai/jev"
KEY_VAR = "AI_GATEWAY_API_KEY"

# One bounded wait per request and no retries: a consumer runs once per
# invocation and reports a failed batch rather than looping on it.
TIMEOUT_SECONDS = 10

# Jev's window is 32k tokens. This is what a consumer batches `state` against,
# leaving room for the questions and the model's own output. Characters, not
# tokens: the client does not count tokens.
STATE_CHAR_BUDGET = 96_000


class JevUnavailable(Exception):
    """The gateway key is not set, so Jev cannot be asked."""


class JevError(Exception):
    """The gateway refused or garbled a request."""


@dataclass
class Answer:
    kind: str
    value: object
    probabilities: dict
    confidence: object


@dataclass
class Result:
    answers: dict
    input_tokens: int
    output_tokens: int
    market_cost: str


def boolean(instructions: str, true: str, false: str) -> dict:
    """A yes/no question. The answer's value is the probability of `true`."""
    return {
        "type": "boolean",
        "instructions": instructions,
        "criteria": {"true": true, "false": false},
    }


def choice(instructions: str, options: dict) -> dict:
    """Pick one option. `options` maps each option to its description."""
    return {"type": "choice", "instructions": instructions, "criteria": dict(options)}


def score(instructions: str, labels: list) -> dict:
    """A 0..1 score over ordered buckets. `labels` names bucket 0, 1, 2, ..."""
    return {"type": "score", "instructions": instructions, "criteria": list(labels)}


def _api_key() -> str:
    key = os.environ.get(KEY_VAR)
    if not key:
        raise JevUnavailable(f"{KEY_VAR} is not set; export it to ask Jev")
    return key


def post(body: dict) -> dict:
    """Send one evaluate request and decode the JSON reply.

    The only place the network is touched, and the one function tests replace.
    `evaluate` calls it through the module attribute so a monkeypatch takes.
    """
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as reply:
            raw = reply.read()
    except urllib.error.HTTPError as err:
        raise JevError(_describe_http_error(err)) from None
    except urllib.error.URLError as err:
        raise JevError(f"could not reach the gateway: {err.reason}") from None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise JevError("the gateway replied with something other than JSON") from None


def _describe_http_error(err: urllib.error.HTTPError) -> str:
    """One line from an HTTP error: status, the gateway's message, and the credits hint.

    The gateway's error body is `{"error": {"message": ...}}`; some refusals put a
    plain string under `error` instead. Neither carries the key, and this never
    reads the request headers, so the message cannot leak it.
    """
    message = ""
    try:
        body = json.loads(err.read().decode("utf-8"))
        error = body.get("error") if isinstance(body, dict) else None
        if isinstance(error, dict):
            message = str(error.get("message") or "")
        elif isinstance(error, str):
            message = error
    except (UnicodeDecodeError, ValueError, AttributeError):
        pass
    line = f"gateway returned {err.code}"
    if message:
        line += f": {message}"
    if err.code == 403 and "free tier" in message.lower():
        line += " (top up gateway credits, the key is fine)"
    return line


def _answer(key: str, raw: dict, per_question_confidence: dict) -> Answer:
    kind = raw.get("type")
    if kind == "boolean":
        p = raw.get("probability")
        value = p
        probabilities = {"true": p, "false": 1 - p} if p is not None else {}
    elif kind == "choice":
        value = raw.get("choice")
        probabilities = raw.get("probabilities") or {}
    else:
        value = raw.get("score")
        probabilities = raw.get("probabilities") or {}
    # The answer carries its own confidence for choice and score; boolean's sits
    # only under providerMetadata.typesafe.confidence, keyed by question.
    confidence = raw.get("confidence", per_question_confidence.get(key))
    return Answer(kind=kind, value=value, probabilities=probabilities, confidence=confidence)


def evaluate(state: str, questions: dict) -> Result:
    """Ask Jev `questions` about `state` and return the typed answers.

    Reads the key from AI_GATEWAY_API_KEY at call time and nothing else from the
    environment. Raises JevUnavailable when it is unset, ValueError on an empty
    state or question map, and JevError when the gateway fails.
    """
    if not state:
        raise ValueError("state is empty; there is nothing to ask Jev about")
    if not questions:
        raise ValueError("questions is empty; build at least one with boolean, choice, or score")
    _api_key()
    reply = post({"model": MODEL, "state": state, "questions": questions})

    metadata = reply.get("providerMetadata") or {}
    confidences = (metadata.get("typesafe") or {}).get("confidence") or {}
    if not isinstance(confidences, dict):
        confidences = {}
    usage = reply.get("usage") or {}
    answers = {
        key: _answer(key, raw, confidences) for key, raw in (reply.get("answers") or {}).items()
    }
    return Result(
        answers=answers,
        input_tokens=usage.get("inputTokens"),
        output_tokens=usage.get("outputTokens"),
        market_cost=(metadata.get("gateway") or {}).get("marketCost"),
    )
