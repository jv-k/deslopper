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
    return compile_tell(_preset_tell_json(name, preset))


def _preset_tell_json(name, preset="recommended"):
    """A shipped tell as its uncompiled preset entry, for checks on the pattern text."""
    return next(t for t in load_builtin(preset)["tells"] if t["name"] == name)


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


# The tells added from the slop-detector survey (issues #60, #68 and #69). Each positive
# is an example phrase from the issue or from docs/research/slop-tells-survey.md, and
# each negative is honest prose the issue or the survey names as staying out.
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
    # openers. The tutorial phrases are left for an aggressive tell that #71 adds.
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
        "cannot be understated",
        "cannot be emphasised enough",
        "cannot be emphasized enough",
        "at a crossroads",
        "at a pivotal moment",
        "at a turning point",
        "The stakes couldn't be higher.",
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
    # Issue #69 from here on.
    "pithy-fragment": [
        "Dense, not cramped.",
        "Simple, yet effective.",
        "Useful, but incremental.",
        "The grid is new. Dense, not cramped.",
        "The grid is new.  Dense, not cramped.",
        "- Dense, not cramped.",
        "* Fast, never flaky.",
    ],
    "narrative-pivot": [
        "Then something shifted.",
        "Everything changed.",
        "That changes everything.",
        "And then it clicked.",
        "The penny dropped.",
    ],
    "negative-listing": [
        "Not a bug. Not a feature. A design flaw.",
        "No config, no flags, just one binary.",
    ],
    "business-jargon": [
        "deep dive",
        "game changer",
        "paradigm shift",
        "move the needle",
        "secret sauce",
        "low-hanging fruit",
        "double down",
        "lean into",
        "circle back",
        "best-in-class",
        "thought leader",
        "win-win",
        # The inflections a writer reaches for as often as the base form.
        "a real game-changer",
        "Game changers",
        "paradigm shifts",
        "It moves the needle.",
        "We are doubling down on caching.",
        "The team leaned into the rewrite.",
        "Circling back on the cache.",
        "a deep-dive into the cache",
        "two deep dives",
        "thought leadership",
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
    # The last two are CPython 3.9 docs lines (issue #62). A colon or semicolon leads
    # into an explanation, so only a full stop or comma makes the pivot.
    "negation-pivot": [
        "It is not set by default. It is read from the env.",
        "This is not a bug: it's a result of the fact that most decimal fractions",
        "That is not a future statement; it's an ordinary import statement with no",
    ],
    "importance-flag": ["The order matters for hashing."],
    # The Django hits and the tutorial examples the survey lists for signposting.
    # recommended leaves them out, and #71 adds them to the aggressive preset.
    "signposting": [
        "By the end of this tutorial, you will have an app.",
        "To recap, the view returns a response.",
        "Let's dive in.",
        "Let's break this down.",
        "Let's unpack the config.",
        "In this article, we'll build a poll app.",
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
    # No i flag: the capital marks the start of a sentence, so a clause inside a
    # sentence stays silent. A one-word reply such as "No," and the docs label
    # "Optional, but recommended." are not slogans.
    "pithy-fragment": [
        "It is dense, not cramped.",
        "dense, not cramped.",
        "No, not yet.",
        "Yes, but only on Linux.",
        "Okay, not now.",
        "Sure, but later.",
        "Thanks, but no.",
        "Optional, but recommended.",
    ],
    # The survey's lookahead keeps out a clause that goes on past the verb. A
    # condition such as "if something changed" is a test, not a story turn.
    "narrative-pivot": [
        "Everything changed in v2 is listed below.",
        "Re-run the build if something changed.",
        "The hook exits 1 when something changed.",
        "It reports whether anything changed.",
        "Check whether something changed.",
        "It skips the step unless something changed.",
    ],
    "negative-listing": [
        "It takes no flags, no config file, and no env vars.",
        "No, not by default. The cache is opt-in.",
    ],
    "business-jargon": [
        "Double the buffer, then move on.",
        "Lean on the cache.",
        "I thought leaders would object.",
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


# pithy-fragment leans on a capital letter to find the start of a sentence, so an
# i flag would make it fire inside any sentence.
CASE_SENSITIVE_SURVEY_TELLS = {"pithy-fragment"}


def test_survey_tells_are_warn_tier_and_case_insensitive_unless_they_need_case():
    raw = {t["name"]: t for t in load_builtin("recommended")["tells"]}
    for name in SURVEY_TELL_POSITIVES:
        assert raw[name]["tier"] == "warn", name
        if name in CASE_SENSITIVE_SURVEY_TELLS:
            assert "i" not in raw[name].get("flags", ""), name
        else:
            assert raw[name]["flags"] == "i", name


@pytest.mark.parametrize("text", [
    "The grid is new. Dense, not cramped.",
    "The grid is new.  Dense, not cramped.",
    "- Dense, not cramped.",
])
def test_pithy_fragment_points_at_the_fragment_not_what_comes_before(text):
    assert offsets(_preset_tell("pithy-fragment"), text) == [text.index("Dense")]


# The words and patterns that widen existing tells, from the same survey (issue
# #61), and the later fixes that narrowed some of them, labelled inline. Each
# positive is one addition an issue lists, so a dropped alternative fails here by
# name.
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
        # Issue #75: orchestrates only with an abstract or marketing object.
        "It orchestrates the experience.",
        "It orchestrates a seamless rollout.",
        "Orchestrate a symphony of services.",
        "It orchestrates your entire journey.",
        "It orchestrates everything.",
        "It orchestrates collaboration.",
        "It orchestrates the entire transformation.",
        # Issue #99: the -ed and -ing forms, same abstract-object lookahead.
        "It orchestrated the transformation.",
        "We orchestrated a seamless experience.",
        "orchestrating a seamless experience",
        "It is orchestrating your entire journey.",
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
        # Issue #74. The slop forms stay caught once bare "realm" is exempt.
        "in the realm of possibility",
        "It sits in the realm of tests.",
        "the realms of possibility",
        # Issue #97. Near the auth exemption, but no auth noun follows "of".
        "in the realm of the possible",
        "In the realm of AI, models win.",
        "the realm of user experience",
        "the realm of a myriad of options",
        # An auth noun used as a modifier is not an auth noun.
        "in the realm of the user experience",
        "in the realm of the service economy",
        "in the realm of the token economy",
        "the realm of the client-side",
        "in the realm of the server-side rendering",
        "the realm of the possible application",
        "In the realm of every application of AI",
        # Honest krb5 prose that stays flagged. An exemption for a realm name
        # in capitals would also pass "the realm of AI".
        "ANL has a sub realm of TEST.",
        "the Kerberos realms of interest",
        # A possessive makes the auth noun a modifier, so the exemption does not apply.
        "It sits in the realm of the user's experience.",
        "It sits in the realm of the user’s experience.",
        "the realm of the users' needs",
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
        "Several sources claim it scales.",
        "Several sources report that it scales.",
        "Several publications suggest it scales.",
        "Several sources note the cost.",
        "Several sources said it scales.",
        "Several publications reported the cost.",
        "Several sources claimed it scales.",
        "Several sources suggested it scales.",
        "Several sources noted the cost.",
        # Issue #95. Both entries take one verb list in the same tenses: present,
        # past, and have/has with the past participle.
        "Experts believe it scales.",
        "Experts believed it scales.",
        "Experts have believed it for years.",
        "Experts say it scales.",
        "Experts said it scales.",
        "Experts have said it scales.",
        "Experts suggest it scales.",
        "Experts suggested it scales.",
        "Experts has suggested it scales.",
        "Experts agree it scales.",
        "Experts agreed it scales.",
        "Experts have agreed it scales.",
        "Experts claim it scales.",
        "Experts claimed it scales.",
        "Experts have claimed it scales.",
        "Experts report that it scales.",
        "Experts reported the cost.",
        "Experts have reported the cost.",
        "Experts note the cost.",
        "Experts noted the cost.",
        "Experts have noted the cost.",
        "Several sources believe it scales.",
        "Several sources believed it scales.",
        "Several sources have believed it for years.",
        "Several sources agree it scales.",
        "Several publications agreed it scales.",
        "Several sources have agreed it scales.",
        "Several sources have said it scales.",
        "Several sources have suggested it scales.",
        "Several sources have claimed it scales.",
        "Several sources have reported the cost.",
        "Several publications has reported the cost.",
        "Several sources have noted the cost.",
        "According to several sources, it scales.",
        "according to several publications, it scales.",
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
    "filler-verb": [
        "Navigate to the settings page.",
        # Issue #75. Orchestration of concrete things is the honest technical sense.
        "Kubernetes orchestrates containers.",
        "It orchestrates the jobs.",
        "The scheduler orchestrates the build steps.",
        "Orchestrate runs your jobs.",
        "Use a tool that can orchestrate deployments.",
        # An abstract-sounding word that only names a concrete thing.
        "It orchestrates the comprehensive test suite.",
        "It orchestrates the build success check.",
        "It orchestrates the payment journey service.",
        "The platform orchestrates your entire workflow.",
        # Issue #99: the -ed and -ing forms before a concrete object.
        "Kubernetes orchestrated the rollout of the containers.",
        "It orchestrated the jobs.",
        "It is orchestrating the build steps.",
        "orchestrating deployments across regions",
    ],
    # Issue #74. "Realm" as the authentication term, not the inflated word.
    "inflated-word": [
        "Create a Keycloak realm.",
        "the Kerberos realm",
        "Add the user in the realm.",
        "Each realm has its own users.",
        # Issue #97. "Realm of" before an auth noun. The first two come from
        # the issue. The rest come from the MIT krb5 docs, RFC 4120 and the
        # Keycloak server admin guide.
        "Set the realm of the client.",
        "the realm of the token",
        "where realm is the realm of your client",
        "The realm-admin role can administer the realm of the user.",
        "substituting the realm of the principal for $0",
        "find the path between its realm and the realm of the server",
        "the Kerberos realm of the host",
        "A server needs a tag for each realm of the clients it will serve.",
        "subtags for all the realms of servers it will need",
        "Do not use untrusted servers to determine the realm of a host.",
        "the realm of the KDC issuing the TGS ticket",
        "if it is not the realm of the client principal",
        "The name and realm of the delegated principal identity.",
        "principals registered in the realm of the compromised KDC",
    ],
    "vague-attribution": [
        "Config merges several sources in order.",
        # Issue #95. Each verb's noun form after have/has is not a reporting verb.
        "The experts have beliefs we can test.",
        "Several sources have a say in the order.",
        "The experts have suggestions for the API.",
        "Several sources have agreements with us.",
        "Several sources have claims on the lock.",
        "The experts have reports to file.",
        "Several sources have notes on the draft.",
        "The experts have a say in the order.",
        "The experts have agreements with us.",
        "The experts have claims on the lock.",
        "The experts have notes on the draft.",
        "Several sources have beliefs we can test.",
        "Several sources have suggestions for the API.",
        "Several sources have reports to file.",
        # A form of the verb outside the tenses the tell takes.
        "Experts reporting tools ship today.",
        # "According to" fires only before "several sources".
        "Config merges several sources according to their order.",
    ],
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
        # Near the technical uses issue #72 exempts, still intensifiers.
        "It is absolutely necessary.",
        "You absolutely must run it.",
        "It is incredibly useful.",
        "It is deeply important.",
        "We can deeply customize it.",
        "It is fundamentally different.",
        "It is truly immutable.",
        "We care as deeply as anyone.",
        "It is positioned as absolutely essential.",
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
        "I don't have access to the logs.",
    ],
    "unicode-arrow": ["Open the menu → it saves.", "Settings → General"],
}

AGGRESSIVE_WIDENED_NEGATIVES = {
    "generic-conclusion": ["The ring buffer wraps in the end state."],
    # Issue #72. Honest technical uses from the MDN and Django docs, where the
    # word names a position, a depth, or a representation, not a degree.
    "strong-intensifier": [
        "The menu is absolutely positioned.",
        "Absolutely position the badge.",
        "Absolutely-positioned elements leave the flow.",
        "Avoid absolutely positioning the footer.",
        "The element is not absolutely or fixed positioned.",
        "Auto-sized absolutely and fixed-positioned elements shrink.",
        "The box is positioned absolutely.",
        "It walks a deeply nested tree.",
        "It walks a deeply-nested tree.",
        "Avoid deeply nesting the lists.",
        "Lists can be nested as deeply as needed.",
        "The badge absolutely positions itself.",
        "Lists may nest as deeply as desired.",
        "Nested thenables are deeply flattened to one promise.",
        "It is fundamentally represented as a count of nanoseconds.",
        "The badges get a truly random hue.",
    ],
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


# Issue #101. The recommended negation-pivot takes only a full stop or a comma
# between the clauses (issue #62). The aggressive layer takes the colon and the
# semicolon. The two CPython 3.9 docs lines are honest prose, and they are the
# known cost of opting in to aggressive.
NEGATION_PIVOT_JOINED_POSITIVES = [
    "It's not a bug; it's a feature.",
    "It's not a bug: it's a feature.",
    "This isn't about speed; it's about trust.",
    "This is not a bug: it's a result of the fact that most decimal fractions",
    "That is not a future statement; it's an ordinary import statement with no",
    "Not because it is slow; because it is wrong.",
    "You don't need more tests: you need better ones.",
    # The second clause takes every subject and verb the first one does.
    "They were not wrong; they were just early.",
    "These are not bugs; these are the features.",
]

NEGATION_PIVOT_JOINED_NEGATIVES = [
    # A full stop or a comma is the recommended tell's form, so this one stays quiet.
    "It's not a bug. It's a feature.",
    "This isn't about speed, it's about trust.",
    # A colon or a semicolon that leads into something other than the pivot.
    "It is not set by default; the env sets it.",
    "This is not supported: see the docs.",
    "It is not a bug. Note: it's a feature.",
]


def test_vague_attribution_misses_a_clause_between_noun_and_verb_by_design():
    # Issue #95 decision: a clause between the noun and the verb is a deliberate
    # miss. Catching it would mean matching across arbitrary text.
    text = "Several sources, including X, say it scales."
    assert not offsets(_preset_tell("vague-attribution"), text)


# The tells from issues #60 and #61 whose patterns hold an apostrophe. Each takes a
# curly one as well as a straight one (issue #63), so the tell still names the slop
# when curly-quote is turned off.
CURLY_APOSTROPHE_TELLS = [
    ("recommended", "not-just-x-but-y"),
    ("recommended", "throat-clearing"),
    ("recommended", "chatbot-phrase"),
    ("recommended", "sycophancy"),
    ("recommended", "real-problem-reframe"),
    ("recommended", "false-suspense"),
    ("recommended", "emphasis-crutch"),
    ("recommended", "staged-candor"),
    ("recommended", "mic-drop"),
    ("recommended", "negation-pivot"),
    ("aggressive", "cutoff-disclaimer"),
    ("aggressive", "negation-pivot-joined"),
]

APOSTROPHE_CLASS = "['’]"


@pytest.mark.parametrize("preset,name", CURLY_APOSTROPHE_TELLS)
def test_survey_tell_has_no_straight_only_apostrophe(preset, name):
    raw = _preset_tell_json(name, preset)
    source = raw.get("pattern") or "|".join(raw["words"])
    assert "'" in source, f"{name} has no apostrophe, so it does not belong in the list"
    assert "'" not in source.replace(APOSTROPHE_CLASS, ""), (
        f"{name} matches only a straight apostrophe somewhere: {source!r}"
    )


def _curly_cases():
    tables = (
        ("recommended", SURVEY_TELL_POSITIVES),
        ("recommended", WIDENED_POSITIVES),
        ("aggressive", AGGRESSIVE_WIDENED_POSITIVES),
        ("aggressive", {"negation-pivot-joined": NEGATION_PIVOT_JOINED_POSITIVES}),
    )
    wanted = set(CURLY_APOSTROPHE_TELLS)
    return [
        (preset, name, text)
        for preset, name, text in _cases(*tables)
        if (preset, name) in wanted and "'" in text
    ]


def test_every_curly_apostrophe_tell_has_a_case_with_an_apostrophe():
    covered = {(preset, name) for preset, name, _text in _curly_cases()}
    assert covered == set(CURLY_APOSTROPHE_TELLS)


@pytest.mark.parametrize("preset,name,text", _curly_cases())
def test_survey_tell_flags_the_curly_apostrophe_form(preset, name, text):
    tell = _preset_tell(name, preset)
    curly = text.replace("'", "’")
    assert offsets(tell, curly), f"{name} should flag: {curly!r}"
    assert offsets(tell, curly) == offsets(tell, text)


def test_new_aggressive_tells_are_warn_tier():
    raw = {t["name"]: t for t in load_builtin("aggressive")["tells"]}
    for name in ("strong-intensifier", "unicode-arrow"):
        assert raw[name]["tier"] == "warn", name


# The survey tells that go into the aggressive layer (issue #70). As in the
# recommended tables, each positive is an example phrase from the survey and each
# negative is a false-positive note from it.
AGGRESSIVE_SURVEY_TELL_POSITIVES = {
    "missing-piece": [
        "This is the missing piece.",
        "the missing link",
        "the gap nobody noticed",
        "the blind spot everyone missed",
        "A missing ingredient in most teams.",
        "the missing layer between tools",
        "This is the missing link in our stack.",
        "the gap no one saw",
        "the blind spot most people ignored",
    ],
    "contrarian-hook": [
        "Most people think caching is easy. They're wrong.",
        "Most teams get this backwards.",
        "Everyone assumes the cache is warm. That's wrong.",
    ],
    "overreach": [
        "the only way to",
        "the single most important",
        "above all else",
        "there's no denying",
        "There is no denying it.",
        "It is arguably the most useful flag.",
        "the only real solution",
    ],
    "invented-concept-label": [
        "the supervision paradox",
        "the acceleration trap",
        "workload creep",
        "the context tax",
        "The review treadmill",
    ],
    # Issue #71 from here on. The tutorial phrases recommended's signposting
    # leaves out, with the survey's Django hits, which are tutorial prose.
    "tutorial-signposting": [
        "Let's dive in.",
        "Let's dive into the config.",
        "Let's delve into it.",
        "Let's break this down.",
        "Let's break it down.",
        "Let's unpack the config.",
        "Let's explore the API.",
        "Let’s dive in.",
        "In this article, we'll build a poll app.",
        "In this guide, we'll build a poll app.",
        "In this post I'll show the fix.",
        "By the end of this guide",
        "By the end of this tutorial, you will have an app.",
        "To recap, the view returns a response.",
    ],
    "contrast-adverb": [
        "It is not simply a cache.",
        "rather than merely storing it",
        "less like a tool and more like a colleague",
        "is genuinely useful",
        "It isn't solely a parser.",
    ],
    # Only the low-noise tokens: the reversal tail and the per-item tail.
    "strawman-tail": [
        "it keeps one copy, not one per caller",
        "the join goes from chunk to blob, not the other way around",
        "Data flows from A to B, not vice versa.",
        "It reads the head, not the reverse.",
        "It runs once, not once for each file.",
    ],
    "restatement-marker": [
        "In other words",
        "In other words, the cache is a dict.",
        "Put simply",
        "Put simply, it caches.",
        "Simply put",
        "Simply put, it caches.",
        "Put differently",
        "Said differently, it caches.",
        "To put it another way",
        "To put it simply, it caches.",
        "What this means is",
        "What this means is that the cache is cold.",
        "Put simply it caches.",
    ],
    "numbered-lead-in": [
        "Three key reasons:",
        "There are three key reasons: speed, size and cost.",
        "Here are the five",
        "Here are the five rules:",
        "There are three main",
        "There are two main branches: main and dev.",
        "Two core ideas: caching and retries.",
        "Three key design reasons:",
        "Here are two examples:",
    ],
    # The survey's examples less the two the issue drops (seams, quietly).
    "claude-figurative": [
        "load-bearing",
        "This check is load-bearing.",
        "a load bearing assumption",
        "the change lands",
        "Once the change lands, the cache is warm.",
        "earns its place",
        "Each flag earns its keep.",
        "It earned its place.",
        "the shape of the problem",
    ],
}

AGGRESSIVE_SURVEY_TELL_NEGATIVES = {
    # The survey: missing piece appears in puzzle and data-gap prose.
    "missing-piece": [
        "Each row flags a missing piece of data.",
        "The box shipped with a missing piece from the jigsaw.",
        "Fix the missing link to the changelog.",
        "It reports a missing piece of code.",
        # The opposite claim: a gap that people did see.
        "the gap everyone noticed",
        "the gap everyone saw",
    ],
    # The survey's three Django hits are "the only way to" in honest reference
    # prose, and the survey lists the same phrase as an example to flag. A line
    # regex cannot tell them apart, so the aggressive tell accepts that risk (the
    # survey rates it medium) and recommended stays silent on it: see
    # test_honest_only_way_to_stays_out_of_recommended. What stays silent here
    # is prose near the phrases that makes no absolute claim.
    "overreach": [
        "It is the only flag.",
        "There is no denial of service.",
        "Above all, run the tests.",
    ],
    # The first half alone is medium risk, so it stays silent.
    "contrarian-hook": [
        "Most people think of a cache as a dict.",
        "Most people think caching is easy. It can be.",
    ],
    # The survey: real terms exist. Shell docs name the EXIT trap.
    "invented-concept-label": [
        "the birthday paradox",
        "scope creep",
        "Feature creep slows the release.",
        "Set the EXIT trap to clean up.",
        "Set the exit trap to clean up.",
        "the income tax",
        "the sales tax",
        "the poverty trap",
        "the digital divide",
        "the fiscal cliff",
        "the Fermi paradox",
        "the hedonic treadmill",
        # creep the verb, not the noun.
        "Costs creep higher every year.",
        "Values can creep.",
        "Memory use tends to creep over time.",
        "Errors creep through.",
        "They creep in slowly.",
    ],
    # The essay closers belong to recommended's signposting, so the aggressive
    # tell does not flag them a second time.
    "tutorial-signposting": [
        "In conclusion, the cache works.",
        "Without further ado",
        "Dive into the code to learn more.",
        "In this article, the cache is a dict.",
        "By the end of this week, it ships.",
        "Let it explore the tree.",
    ],
    # The survey's Django hits ("rather than simply joining", "is not simply
    # Python") read the same as its examples, so the aggressive tell accepts that
    # risk and recommended stays silent on them: see
    # test_honest_aggressive_hits_stay_out_of_recommended.
    "contrast-adverb": [
        "It is simply a cache.",
        "It looks less like a bug.",
        "It is merely a stub.",
        # Instructions, not a definition by contrast.
        "Do not simply copy the file.",
        "You should not simply delete the row.",
    ],
    # The issue keeps the bare "rather than" and "instead of" tails out: the
    # survey rates them high risk, with 275 Django lines on "rather than".
    "strawman-tail": [
        "the reader walks the index, rather than walking the whole tree",
        "It reads the cache instead of the disk.",
        "It reads the file rather than the socket.",
        "Use the reverse order, not the default.",
        "Pass one, not two.",
        "Sort it, not the reverse order.",
        "Use A, not the inverse matrix.",
    ],
    # The survey: one Django hit is the imperative "simply put a".
    "restatement-marker": [
        "Simply put a file in the folder.",
        "Put the file simply in the root.",
        "What this means for you is listed below.",
        "What that means is unclear.",
    ],
    # The survey: human docs count list items too.
    "numbered-lead-in": [
        "There are three files in the folder.",
        "Run these three steps:",
        "The two main files are listed below.",
        "Here are the files.",
        "Here are the two files.",
        "Here are two files you need.",
        "There are three main causes of the bug.",
    ],
    # The issue drops seams and quietly, which have honest technical meanings.
    # The survey's Django hit is the quietly line.
    "claude-figurative": [
        "browsers will quietly ignore the header",
        "It quietly drops the packet.",
        "Put a test at each of the seams.",
        "The bearing takes the load.",
        "The plane lands at noon.",
        "It earns interest.",
        "The shape of the array is (2, 3).",
    ],
}


@pytest.mark.parametrize("name,text", [
    (name, text) for name, texts in AGGRESSIVE_SURVEY_TELL_POSITIVES.items() for text in texts
])
def test_aggressive_survey_tell_flags_its_example(name, text):
    assert offsets(_preset_tell(name, "aggressive"), text), f"{name} should flag: {text!r}"


@pytest.mark.parametrize("name,text", [
    (name, text) for name, texts in AGGRESSIVE_SURVEY_TELL_NEGATIVES.items() for text in texts
])
def test_aggressive_survey_tell_leaves_honest_prose_alone(name, text):
    assert not offsets(_preset_tell(name, "aggressive"), text), f"{name} false positive: {text!r}"


def test_aggressive_survey_tells_are_warn_tier_and_case_insensitive():
    raw = {t["name"]: t for t in load_builtin("aggressive")["tells"]}
    for name in AGGRESSIVE_SURVEY_TELL_POSITIVES:
        assert raw[name]["tier"] == "warn", name
        assert raw[name]["flags"] == "i", name


@pytest.mark.parametrize("text", [
    # The survey's three Django hits for overreach are this honest reference use.
    "The only way to set the timeout is the env var.",
    "This is the only way to change the cache key.",
])
def test_honest_only_way_to_stays_out_of_recommended(text):
    for raw in load_builtin("recommended")["tells"]:
        assert not offsets(compile_tell(raw), text), f"{raw['name']} false positive: {text!r}"


@pytest.mark.parametrize("text", [
    # The survey's Django hits for contrast-adverb and restatement-marker, and
    # the civil-engineering sense of load-bearing it notes for claude-figurative.
    # The aggressive tells flag these, and only that opt-in layer may.
    "It joins the tables rather than simply joining the rows.",
    "The template language is not simply Python.",
    "In other words, the view returns a response.",
    "Do not remove a load-bearing wall.",
])
def test_honest_aggressive_hits_stay_out_of_recommended(text):
    for raw in load_builtin("recommended")["tells"]:
        assert not offsets(compile_tell(raw), text), f"{raw['name']} false positive: {text!r}"


def test_arrow_stays_out_of_the_recommended_emoji_tell():
    # UI paths such as "Settings → General" use the arrow honestly, so only the
    # opt-in aggressive layer flags it.
    tells = [t for t in load_builtin("recommended")["tells"] if t["name"] == "emoji"]
    assert tells
    for raw in tells:
        assert not offsets(compile_tell(raw), "Settings → General")


@pytest.mark.parametrize("text", NEGATION_PIVOT_JOINED_POSITIVES)
def test_negation_pivot_joined_flags_a_colon_or_semicolon_pivot(text):
    tell = _preset_tell("negation-pivot-joined", "aggressive")
    assert offsets(tell, text), f"should flag: {text!r}"


@pytest.mark.parametrize("text", NEGATION_PIVOT_JOINED_NEGATIVES)
def test_negation_pivot_joined_leaves_other_lines_alone(text):
    tell = _preset_tell("negation-pivot-joined", "aggressive")
    assert not offsets(tell, text), f"false positive: {text!r}"


@pytest.mark.parametrize("text", NEGATION_PIVOT_JOINED_POSITIVES)
def test_recommended_negation_pivot_leaves_the_joined_form_to_aggressive(text):
    # The two tells split the cases, so a line never smells twice for one pivot.
    assert not offsets(_preset_tell("negation-pivot"), text), f"recommended flags: {text!r}"


def test_negation_pivot_joined_is_warn_tier_and_case_insensitive():
    raw = _preset_tell_json("negation-pivot-joined", "aggressive")
    assert raw["tier"] == "warn"
    assert raw["flags"] == "i"


def test_no_aggressive_tell_shares_a_name_with_a_recommended_tell():
    # Stricter than the (name, phase) rule in test_config: a shared name at a
    # different phase would still make two tells read as one in the output.
    recommended = {t["name"] for t in load_builtin("recommended")["tells"]}
    aggressive = {t["name"] for t in load_builtin("aggressive")["tells"]}
    assert not recommended & aggressive
