import json
import os
import stat
import sys

import pytest

from deslopper import gum, jev

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


@pytest.fixture(autouse=True)
def no_hook_git_env(monkeypatch):
    """Drop the git variables a hook inherits. In a worktree's pre-commit hook git
    exports GIT_DIR, and discovery's `git ls-files` in a temp folder would read
    this repo instead of the folder."""
    for name in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def jev_cache_home(monkeypatch, tmp_path_factory):
    """Every test caches Jev answers in its own folder, never the real user cache."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path_factory.mktemp("cache-home")))


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


# gum, faked. No test reaches a real gum: by default the suite runs as if gum were not
# installed, and a test that wants the styled layer installs this shim, which records each
# call and prints a marker in place of gum's escapes.

GUM_SHIM = """#!{python}
import json, os, signal, sys, time
args = sys.argv[1:]
stdin = sys.stdin.read() if args[:1] in (["table"], ["format"]) else ""
with open(os.environ["GUM_SHIM_LOG"], "a", encoding="utf-8") as fh:
    fh.write(json.dumps({{"args": args, "stdin": stdin,
                         "clicolor_force": os.environ.get("CLICOLOR_FORCE")}}) + "\\n")
sub = args[0]
if os.environ.get("GUM_SHIM_FAIL"):
    sys.stderr.write("gum: something broke\\n")
    sys.exit(1)
if sub == "format":
    # Like gum, trim the whitespace around the drawing, blank lines and all.
    sys.stdout.write(stdin.strip())
elif sub == "table":
    sys.stdout.write("<table " + " ".join(args[1:]) + ">\\n" + stdin)
elif sub == "style":
    sys.stdout.write("<style " + " ".join(args[1:-2]) + ">" + args[-1] + "</style>\\n")
elif sub == "log":
    sys.stderr.write("<log " + " ".join(args[1:-2]) + ">" + args[-1] + "\\n")
elif sub == "spin":
    # Like gum, run the command after "--" as a child and wait on it. The child's pid
    # goes to the log, so a test can check nothing outlives the spinner.
    import subprocess
    child = subprocess.Popen(args[args.index("--") + 1:])
    with open(os.environ["GUM_SHIM_LOG"] + ".pids", "a", encoding="utf-8") as fh:
        fh.write(str(child.pid) + "\\n")
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    child.wait()
"""


@pytest.fixture(autouse=True)
def no_gum(monkeypatch):
    """Every test starts unattended and without gum, whatever the machine has."""
    monkeypatch.setattr(gum, "binary", lambda: None)
    monkeypatch.delenv("CLICOLOR_FORCE", raising=False)
    monkeypatch.setattr(gum, "_hinted", False)


@pytest.fixture
def gum_shim(monkeypatch, tmp_path_factory):
    """Install the shim as gum and force an attended run. Returns a function that reads
    the recorded calls back, one dict per call."""
    bin_dir = tmp_path_factory.mktemp("gum-bin")
    shim = bin_dir / "gum"
    shim.write_text(GUM_SHIM.format(python=sys.executable), encoding="utf-8")
    shim.chmod(shim.stat().st_mode | stat.S_IEXEC)
    log = bin_dir / "calls.jsonl"
    monkeypatch.setenv("GUM_SHIM_LOG", str(log))
    monkeypatch.setenv("CLICOLOR_FORCE", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(gum, "binary", lambda: str(shim))

    def calls():
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]

    return calls
