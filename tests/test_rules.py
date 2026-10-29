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


def _preset_tell(name, preset="recommended"):
    """A real tell out of a shipped preset.

    Loaded through the same loader the app uses, rather than hand-copied, so these
    regress if the preset does and survive a layout change.
    """
    raw = load_builtin(preset)
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
    # Issue #68 from here on. signposting takes only the essay closers and
    # openers; the tutorial phrases belong to a separate aggressive tell.
    "signposting": [
        "In conclusion, the cache works.",
        "In summary, it builds.",
        "To sum up",
        "Key takeaways",
        "Key takeaway: retries add up.",
        "Without further ado",
    ],
    "urgency-inflation": [
        "cannot be overstated",
        "can't be overstated",
        "more important than ever",
        "has never been more critical",
        "at an inflection point",
        "at a critical juncture",
        "the stakes have never been higher",
    ],
    "stacked-hedge": [
        "could potentially fail",
        "might possibly",
        "may arguably",
        "There could potentially be multiple values.",
    ],
    "tradeoff-dodge": [
        "fast without sacrificing safety",
        "without compromising quality",
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
    # The Django hits the survey lists for signposting are tutorial prose, which
    # recommended leaves to the opt-in layer.
    "signposting": [
        "By the end of this tutorial, you will have an app.",
        "To recap, the view returns a response.",
        "Let's dive in.",
        "Let's break this down.",
        "In this guide, we'll build a poll app.",
        "Conclusions are drawn in the summary.",
    ],
    "urgency-inflation": [
        "This path has never been tested.",
        "The value cannot be empty.",
        "The stakes are low.",
    ],
    "stacked-hedge": ["The call could fail.", "It may be cached."],
    # The survey keeps these out: common in plain technical prose.
    "tradeoff-dodge": [
        "It restarts without losing data.",
        "It runs without requiring a restart.",
    ],
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


# The words and patterns that widen existing tells, from the same survey (issue
# #61). Each positive is one addition the issue lists, so a dropped alternative
# fails here by name.
WIDENED_POSITIVES = {
    "not-just-x-but-y": [
        "not only per type of object, but also per instance",
        "It is not merely a cache but a store.",
        "Not only does it build, it's fast.",
    ],
    "throat-clearing": [
        "It's important to note that tests pass.",
        "It's important to remember the cache.",
        "It's important to understand the flow.",
        "It bears mentioning that it caches.",
        "Importantly, the cache is warm.",
        "Interestingly, it works.",
        "Notably, the run is fast.",
        "Ultimately, this is a choice.",
        "In the realm of build tools, speed wins.",
        "In an era where builds are slow, speed wins.",
        "In a world where builds are slow, speed wins.",
        "Imagine a world where builds are fast.",
        "Picture this: a fast build.",
        "Have you ever wondered why builds are slow?",
        "Since the dawn of computing, builds were slow.",
        "As we navigate the release, keep notes.",
    ],
    "filler-verb": [
        "It elevates the docs.",
        "We embark on a rewrite.",
        "She embarked on a rewrite.",
        "Unleash the cache.",
        "It is unleashing the cache.",
        "This bolsters the case.",
        "It is bolstering the case.",
        "It orchestrates the jobs.",
        "It transcends the old design.",
        "This enhances the output.",
        "It helps you navigate the complexities of config.",
    ],
    "marketing-adjective": [
        "a groundbreaking tool",
        "a holistic view",
        "a multifaceted problem",
        "meticulous care",
        "unparalleled speed",
        "an invaluable aid",
        "a topic of paramount importance",
        "a transformative change",
        "an impactful change",
        "a breathtaking view",
        "a stunning result",
        "a revolutionary tool",
        "a state-of-the-art build",
    ],
    "inflated-word": [
        "the realm of tests",
        "a myriad of options",
        "a plethora of flags",
        "the interconnectedness of parts",
        "a nuanced take",
        "a commendable effort",
        "a noteworthy change",
        "an ever-evolving field",
        "an ever-changing API",
    ],
    "trailing-participle": [
        "It retries, emphasizing delivery.",
        "It shines, symbolizing hope.",
        "It runs, contributing to uptime.",
        "It teaches, cultivating skill.",
        "It spans, encompassing all jobs.",
        "It caches, enhancing speed.",
        "It wins, solidifying its lead.",
        "It ships, cementing trust.",
        "It lands, paving the way for more.",
    ],
    "vague-attribution": [
        "Studies show it scales.",
        "Research suggests it scales.",
        "It is widely believed that it scales.",
        "Observers have cited the cost.",
        "Observers have noted the cost.",
        "Some argue it scales.",
        "Several sources say it scales.",
        "Several publications say it scales.",
    ],
    "chatbot-phrase": [
        "Would you like me to add tests?",
        "If you want, I can add tests.",
        "If you'd like, I can add tests.",
        "Do you want me to add tests?",
        "Is there anything else to add?",
        "Don't hesitate to ask.",
        "I'm happy to help.",
        "Shall I add tests?",
    ],
    "sycophancy": [
        "You're right to push back on that.",
        "That's a fair concern.",
        "That's a fair point.",
        "Good catch!",
        "I hear you.",
    ],
    "fancy-is": [
        "The CLI functions as a hub.",
        "The CLI operates as a hub.",
        "It holds the distinction of being first.",
    ],
    "puffery": [
        "It plays a crucial role in builds.",
        "It plays a pivotal role in builds.",
        "Tests play a vital role.",
        "It plays a key role.",
        "It plays a significant role.",
        "It plays crucial role in essays.",
        "a key turning point",
        "the focal point of the release",
        "an enduring legacy",
        "a rich heritage",
        "a rich cultural heritage",
        "nestled in the config",
        "in the heart of the engine",
        "valuable insights",
    ],
}

WIDENED_NEGATIVES = {
    "filler-verb": ["Navigate to the settings page."],
    "not-just-x-but-y": [
        "The cache is not only keyed by its hash.",
        "It is not just its size.",
    ],
}

AGGRESSIVE_WIDENED_POSITIVES = {
    "strong-intensifier": [
        "It is genuinely fast.",
        "It is truly fast.",
        "It is incredibly fast.",
        "It is absolutely fast.",
        "It is deeply useful.",
        "It is remarkably fast.",
        "It is fundamentally sound.",
    ],
    "generic-conclusion": [
        "At the end of the day, it ships.",
        "It all comes down to tests.",
        "In the end, it ships.",
    ],
    "cutoff-disclaimer": [
        "The figure is not widely documented.",
        "The figure is not widely available.",
        "The figure is not widely disclosed.",
        "Based on the available information, it ships.",
        "Based on available information, it ships.",
        "Nothing in the provided sources says so.",
        "Nothing in the available search results says so.",
        "That does not by itself establish a trend.",
    ],
    "unicode-arrow": ["Open the menu → it saves.", "Settings → General"],
}

AGGRESSIVE_WIDENED_NEGATIVES = {
    "generic-conclusion": ["The ring buffer wraps in the end state."],
}


def _cases(*tables):
    return [
        (preset, name, text)
        for preset, table in tables
        for name, texts in table.items()
        for text in texts
    ]


@pytest.mark.parametrize("preset,name,text", _cases(
    ("recommended", WIDENED_POSITIVES), ("aggressive", AGGRESSIVE_WIDENED_POSITIVES),
))
def test_widened_tell_flags_each_addition(preset, name, text):
    assert offsets(_preset_tell(name, preset), text), f"{name} should flag: {text!r}"


@pytest.mark.parametrize("preset,name,text", _cases(
    ("recommended", WIDENED_NEGATIVES), ("aggressive", AGGRESSIVE_WIDENED_NEGATIVES),
))
def test_widened_tell_leaves_honest_prose_alone(preset, name, text):
    assert not offsets(_preset_tell(name, preset), text), f"{name} false positive: {text!r}"


def test_new_aggressive_tells_are_warn_tier():
    raw = {t["name"]: t for t in load_builtin("aggressive")["tells"]}
    for name in ("strong-intensifier", "unicode-arrow"):
        assert raw[name]["tier"] == "warn", name


def test_arrow_stays_out_of_the_recommended_emoji_tell():
    # UI paths such as "Settings → General" use the arrow honestly, so only the
    # opt-in aggressive layer flags it.
    tells = [t for t in load_builtin("recommended")["tells"] if t["name"] == "emoji"]
    assert tells
    for raw in tells:
        assert not offsets(compile_tell(raw), "Settings → General")
