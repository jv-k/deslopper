import pytest

from deslopper.rules import compile_tell
from deslopper.errors import ConfigError
from deslopper.presets import load_builtin


def offsets(tell, text):
    return list(tell.matcher(text))


def test_regex_kind_yields_all_offsets():
    t = compile_tell({"name": "semi", "tier": "warn", "kind": "regex",
                      "pattern": ";", "message": "m"})
    assert offsets(t, "a; b; c") == [1, 4]
    assert t.key == ("semi", "post-entity")
    assert t.phase == "post-entity"
    assert t.scope == "all"


def test_words_is_sugar_for_regex_with_word_boundaries():
    t = compile_tell({"name": "filler", "tier": "warn",
                      "words": ["enables?", "powers"], "flags": "i", "message": "m"})
    # case-insensitive, word-boundaried, regex fragments honoured
    assert offsets(t, "It Enables and power and powers") == [3, 25]


def test_pattern_takes_phase_and_scope_from_fields():
    t = compile_tell({"name": "x", "tier": "error", "phase": "pre-entity",
                      "scope": "first", "kind": "regex", "pattern": "&mdash;",
                      "message": "m"})
    assert t.phase == "pre-entity"
    assert t.scope == "first"
    assert t.key == ("x", "pre-entity")


def test_bold_bullet_flags_label_then_prose_only():
    bb = {"name": "bold-bullet-lead", "tier": "warn", "kind": "bold-bullet",
          "pattern": r"^(\s*(?:[-*+]|\d+\.)\s+)(\*\*|__)(.+?)\2(.*)$", "message": "m"}
    t = compile_tell(bb)
    assert offsets(t, "- **Lead** then prose") == [2]      # col 3 -> offset 2
    assert offsets(t, "- **Term:** definition") == []      # terminal colon exempt
    assert offsets(t, "- **Whole bold item**") == []       # nothing follows
    assert offsets(t, "1. **N** then prose") == [3]        # numbered lead len 3


def _preset_tell(name):
    """A real tell out of the shipped preset.

    Loaded through the same loader the app uses, rather than hand-copied, so these
    regress if the preset does and survive a layout change.
    """
    raw = load_builtin("recommended")
    return compile_tell(next(t for t in raw["tells"] if t["name"] == name))


@pytest.mark.parametrize("text,col", [
    ("- G1 Unified view of every package", 2),
    ("- **G1** Unified view of every package", 2),
    ("- **NG2** Windows support", 2),
    ("1. FR-3.1 Read the manifest", 3),
    ("  * __AC1__: The suite reports zero failures", 4),
    ("1. **US-1** - *As a maintainer*, I run it", 3),
])
def test_id_label_flags_a_labelled_list_item(text, col):
    assert offsets(_preset_tell("id-label-lead"), text) == [col], f"should flag: {text!r}"


@pytest.mark.parametrize("text", [
    "- S3 buckets are cheap",             # lowercase tail: a subject, not a label
    "- MP4 exports are supported",
    "- **S3 Node:** Consider the option",  # bold running past the label names a thing
    "- Speed delivers performance",        # no digits, no label
    "- G1",                                # nothing labelled
    "G1 Unified view of every package",    # not a list item
    "| G1 | Unified view of every package |",  # a table cell, not a list
    "### G1 Unified view of every package",    # a heading, not a list
])
def test_id_label_exempts_prose_that_merely_starts_with_a_name_and_digit(text):
    assert not offsets(_preset_tell("id-label-lead"), text), f"false positive: {text!r}"


def test_unknown_kind_is_config_error():
    with pytest.raises(ConfigError):
        compile_tell({"name": "x", "tier": "warn", "kind": "nope",
                      "pattern": ".", "message": "m"})


def test_unknown_flag_is_config_error():
    with pytest.raises(ConfigError):
        compile_tell({"name": "x", "tier": "warn", "kind": "regex",
                      "pattern": ".", "flags": "z", "message": "m"})


def test_missing_pattern_and_words_is_config_error():
    with pytest.raises(ConfigError):
        compile_tell({"name": "x", "tier": "warn", "message": "m"})


def test_invalid_regex_is_config_error():
    with pytest.raises(ConfigError):
        compile_tell({"name": "x", "tier": "warn", "kind": "regex",
                      "pattern": "(", "message": "m"})


def test_unknown_tier_is_config_error():
    # Tier is closed to error/warn. An unknown tier used to pass silently and then crash
    # the github formatter; it is now rejected at compile time (exit 2).
    with pytest.raises(ConfigError):
        compile_tell({"name": "x", "tier": "info", "pattern": ".", "message": "m"})


def test_missing_tier_is_config_error():
    with pytest.raises(ConfigError):
        compile_tell({"name": "x", "pattern": ".", "message": "m"})


@pytest.mark.parametrize("kind", ["bold-bullet", "id-label"])
def test_kind_needing_groups_rejects_a_pattern_without_them(kind):
    # These kinds read their capture groups by number. A pattern that lacks them used to
    # raise IndexError mid-lint; a malformed tell has to be a ConfigError (exit 2) instead.
    with pytest.raises(ConfigError):
        compile_tell({"name": "x", "tier": "warn", "kind": kind,
                      "pattern": "foo", "message": "m"})


@pytest.mark.parametrize("text", [
    "This article delves into the details",
    "Let's delve into the internals",
    "Delve into the world of async",       # sentence-initial opener
    "Delves into the specifics below",
    "We delve deeper here",
])
def test_filler_verb_flags_delve_as_a_verb(text):
    assert offsets(_preset_tell("filler-verb"), text), f"should flag: {text!r}"


@pytest.mark.parametrize("text", [
    "Delve has the same problem and has to run headless",  # the Go debugger
    "Debugging with Delve requires headless mode",
    "Delve is a debugger for Go",
])
def test_filler_verb_leaves_delve_the_proper_noun_alone(text):
    # `delve` is a filler verb; `Delve` is a tool. Capitalised and not followed
    # by into/deeper, it is the proper noun, so the tell must not fire.
    assert not offsets(_preset_tell("filler-verb"), text), f"false positive: {text!r}"


def test_middle_dot_leaves_the_white_bullet_alone():
    # ◦ (U+25E6) is the separator the message points at for a status line or a
    # footer, where a comma reads wrong, so neither spelling of the tell fires on it.
    for raw in (t for t in load_builtin("recommended")["tells"] if t["name"] == "middle-dot"):
        assert not offsets(compile_tell(raw), "PR #12 ◦ owner aaaa1111 ◦ ledger 2m")


def test_middle_dot_message_names_the_separator_to_use():
    # Both spellings of the tell, the character and the HTML entity, say what
    # to write instead where a separator is needed.
    tells = [t for t in load_builtin("recommended")["tells"] if t["name"] == "middle-dot"]
    assert len(tells) == 2
    for tell in tells:
        assert "◦" in tell["message"], tell["message"]


# The tells added from the slop-detector survey (issue #60). Each positive is an
# example phrase from the issue, and each negative is honest prose the issue names
# as staying out.
SURVEY_TELL_POSITIVES = {
    "false-exclusivity": [
        "Nobody talks about the cost.",
        "Here's what nobody tells you about caching.",
        "What no one tells you is",
        "The part everyone misses",
        "What most people get wrong",
        "No one is talking about this.",
        "Most people miss the point.",
        "Few people skip the warm-up.",
    ],
    "hidden-truth": [
        "The quiet truth is that tests rot.",
        "the hidden cost of retries",
        "The uncomfortable truth:",
        "the dirty little secret",
        "the inconvenient truth",
    ],
    "real-problem-reframe": [
        "The real problem isn't speed, it's trust.",
        "Latency isn't the bottleneck.",
        "It was never about the code.",
        "The question isn't X. It's Y.",
    ],
    "false-suspense": [
        "Here's the thing:",
        "Here's the kicker.",
        "Here's where it gets interesting.",
        "Here's why this matters.",
        "Here's what I learned.",
        "The kicker",
    ],
    "rhetorical-self-answer": [
        "The result? Devastating.",
        "The catch? It only runs on Linux.",
        "The worst part? Nobody saw it coming.",
    ],
    "emphasis-crutch": [
        "Let that sink in.",
        "Read that again.",
        "Full stop.",
        "Make no mistake",
        "I'll say it again:",
        "Yes, really.",
    ],
    "staged-candor": [
        "And honestly?",
        "Honestly? It depends.",
        "Honest take:",
        "Let's be honest,",
        "To be frank",
        "If I'm being honest",
        "The honest answer",
    ],
    "mic-drop": [
        "That's the whole point.",
        "And that's okay.",
        "That's the beauty of it.",
        "This is what good tooling looks like.",
        "It matters.",
    ],
    "negation-pivot": [
        "It's not a bug. It's a feature.",
        "This isn't about speed, it's about trust.",
        "Not because it is slow. Because it is wrong.",
        "You don't need more tests. You need better ones.",
    ],
    "importance-flag": [
        "This matters because",
        "Why this matters",
        "That distinction matters.",
        "matters more than ever",
    ],
}

SURVEY_TELL_NEGATIVES = {
    "false-exclusivity": ["No one can write to the file."],
    "real-problem-reframe": [
        "The real problem is a race in the cache.",
        "The problem isn't reproducible on Linux.",
        "The question is not answered in the docs.",
    ],
    "false-suspense": ["Here's how to run it.", "Here's the output of the command."],
    "rhetorical-self-answer": ["What is the result? See below."],
    "emphasis-crutch": ["Use a full stop at the end."],
    "staged-candor": ["He answered honestly."],
    "mic-drop": ["It matters which order you pass them in."],
    "negation-pivot": ["It is not set by default. It is read from the env."],
    "importance-flag": ["The order matters for hashing."],
}


@pytest.mark.parametrize("name,text", [
    (name, text) for name, texts in SURVEY_TELL_POSITIVES.items() for text in texts
])
def test_survey_tell_flags_its_example(name, text):
    assert offsets(_preset_tell(name), text), f"{name} should flag: {text!r}"


@pytest.mark.parametrize("name,text", [
    (name, text) for name, texts in SURVEY_TELL_NEGATIVES.items() for text in texts
])
def test_survey_tell_leaves_honest_prose_alone(name, text):
    assert not offsets(_preset_tell(name), text), f"{name} false positive: {text!r}"


def test_survey_tells_are_warn_tier_and_case_insensitive():
    raw = {t["name"]: t for t in load_builtin("recommended")["tells"]}
    for name in SURVEY_TELL_POSITIVES:
        assert raw[name]["tier"] == "warn", name
        assert raw[name]["flags"] == "i", name
