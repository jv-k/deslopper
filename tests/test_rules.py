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
