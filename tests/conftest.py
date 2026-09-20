import json
import os

import pytest

from deslopper import jev

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")

FAKE_KEY = "test-key-not-real"


@pytest.fixture
def fixtures_dir():
    return FIXTURES


# The gateway, faked. A test that triages hands `canned_jev` the verdicts it
# wants and reads the request bodies back off the list it returns.


def jev_envelope(verdicts, keys, tokens=(1577, 0), cost="0.000066"):
    """A gateway reply answering `keys` in order from `verdicts`, cycling. Each
    verdict is a (choice, probability) pair; the other option gets the rest."""
    answers = {}
    for i, key in enumerate(keys):
        choice, probability = verdicts[i % len(verdicts)]
        other = "keep" if choice == "rewrite" else "rewrite"
        answers[key] = {
            "type": "choice",
            "choice": choice,
            "probabilities": {choice: probability, other: 1 - probability},
            "confidence": probability,
        }
    return {
        "answers": answers,
        "usage": {"inputTokens": tokens[0], "outputTokens": tokens[1]},
        "providerMetadata": {"gateway": {"marketCost": cost}},
    }


def canned_jev(monkeypatch, verdicts, **envelope):
    """Swap `jev.post` for a transport answering every question from `verdicts`,
    export a fake key, and return the list the bodies are recorded on."""
    monkeypatch.setenv(jev.KEY_VAR, FAKE_KEY)
    calls = []

    def post(body):
        calls.append(body)
        return jev_envelope(verdicts, list(body["questions"]), **envelope)

    monkeypatch.setattr(jev, "post", post)
    return calls


# The output schema's finding sub-schema and a stdlib walk over it. jsonschema
# is not a dependency, and the sub-schema uses only required, properties, type,
# enum, minimum and maximum, each of which is checked here.

_JSON_TYPES = {"string": str, "integer": int, "number": (int, float)}


def finding_schema():
    from importlib import resources
    text = resources.files("deslopper.schema").joinpath("output.schema.json").read_text(encoding="utf-8")
    return json.loads(text)["properties"]["findings"]["items"]


def check_finding(item, schema):
    props = schema["properties"]
    for key in schema["required"]:
        assert key in item, key
    for key, value in item.items():
        assert key in props, f"{key} is not in the schema"
        rule = props[key]
        if "enum" in rule:
            assert value in rule["enum"], (key, value)
        if "type" in rule:
            assert isinstance(value, _JSON_TYPES[rule["type"]]), (key, value)
            assert not isinstance(value, bool), (key, value)
        if "minimum" in rule:
            assert value >= rule["minimum"], (key, value)
        if "maximum" in rule:
            assert value <= rule["maximum"], (key, value)
