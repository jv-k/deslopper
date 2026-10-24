import json

import pytest

from deslopper.findings import Finding, LintResult
from decimal import Decimal

from deslopper.triage import Triage
from deslopper.report import (exit_code, excerpt, format_github, format_json, format_text,
                              lint_view, rule_lines, summary_line)
from tests.conftest import check_finding as _check_finding, finding_schema as _finding_schema


def sample():
    return LintResult(
        findings=[
            Finding("a.md", 3, 5, "error", "em-dash", "em dash in prose"),
            Finding("a.md", 4, 1, "warn", "semicolon", "semi: a%b\nnext"),
        ],
        unreadable=["b.md"],
    )


def test_format_text():
    out = format_text(sample())
    assert out.splitlines()[0] == "a.md:3:5 [error] em-dash: em dash in prose"


def test_format_github_maps_tier_and_encodes():
    out = format_github(sample())
    lines = out.splitlines()
    assert lines[0] == "::error file=a.md,line=3,col=5::em-dash - em dash in prose"
    # warn -> warning, and the message is percent-encoded (% -> %25, newline -> %0A)
    assert lines[1] == "::warning file=a.md,line=4,col=1::semicolon - semi: a%25b%0Anext"


def test_format_github_escapes_delimiters_in_the_path():
    # , and : delimit workflow-command properties, so a path carrying them must escape
    # them or the annotation points nowhere.
    r = LintResult(findings=[Finding("a,b:c.md", 1, 2, "error", "x", "m")])
    assert format_github(r).strip() == "::error file=a%2Cb%3Ac.md,line=1,col=2::x - m"


def test_format_json_envelope():
    out = json.loads(format_json(sample()))
    assert out["summary"] == {"errors": 1, "warnings": 1, "unreadable": 1}
    assert out["unreadable"] == ["b.md"]
    assert out["findings"][0] == {
        "path": "a.md", "line": 3, "col": 5, "tier": "error",
        "name": "em-dash", "message": "em dash in prose",
    }


def test_summary_line():
    assert summary_line(sample(), False) == "✖ 1 error(s), 1 warning(s), 1 unreadable"
    assert summary_line(sample(), True).endswith("[strict]")
    assert summary_line(LintResult(), False) == "✔ no slop found"
    warn_only = LintResult(findings=[Finding("a.md", 1, 1, "warn", "x", "m")])
    assert summary_line(warn_only, False) == "! 0 error(s), 1 warning(s)"


def test_exit_code():
    clean = LintResult()
    assert exit_code(clean, False) == 0
    warn_only = LintResult(findings=[Finding("a.md", 1, 1, "warn", "x", "m")])
    assert exit_code(warn_only, False) == 0
    assert exit_code(warn_only, True) == 1
    err = LintResult(findings=[Finding("a.md", 1, 1, "error", "x", "m")])
    assert exit_code(err, False) == 1
    unreadable = LintResult(unreadable=["b.md"])
    assert exit_code(unreadable, False) == 1


def annotated():
    return LintResult(
        findings=[
            Finding("a.md", 3, 5, "error", "em-dash", "em dash in prose",
                    verdict="keep", probability=0.93),
            Finding("a.md", 4, 1, "warn", "semicolon", "semi",
                    verdict="rewrite", probability=0.88),
            Finding("a.md", 5, 1, "warn", "hedge", "hedge"),
        ],
    )


def test_finding_verdict_fields_default_to_none():
    f = Finding("a.md", 1, 1, "warn", "x", "m")
    assert f.verdict is None
    assert f.probability is None


@pytest.mark.parametrize("kwargs", [
    {"verdict": "keep"},
    {"probability": 0.5},
    {"verdict": "maybe", "probability": 0.5},
    {"verdict": "keep", "probability": 1.5},
    {"verdict": "keep", "probability": -0.1},
])
def test_finding_rejects_a_half_or_out_of_range_verdict(kwargs):
    # The pair is one unit and the schema is the contract, so a Finding that could
    # not render as valid JSON cannot be built in the first place.
    with pytest.raises(ValueError):
        Finding("a.md", 1, 1, "warn", "x", "m", **kwargs)


def test_finding_accepts_the_probability_bounds():
    assert Finding("a.md", 1, 1, "warn", "x", "m", verdict="keep", probability=0).probability == 0
    assert Finding("a.md", 1, 1, "warn", "x", "m", verdict="rewrite", probability=1).probability == 1


def test_format_text_appends_verdict_only_when_present():
    lines = format_text(annotated()).splitlines()
    assert lines[0] == "a.md:3:5 [error] em-dash: em dash in prose [keep 0.93]"
    assert lines[1] == "a.md:4:1 [warn] semicolon: semi [rewrite 0.88]"
    assert lines[2] == "a.md:5:1 [warn] hedge: hedge"


# Styled, the probability becomes a five-slot gauge: filled slots in the confidence
# colour, the rest dim. Piped output above keeps the number and the pinned grammar.


def test_format_json_carries_verdict_only_on_judged_findings():
    findings = json.loads(format_json(annotated()))["findings"]
    assert findings[0]["verdict"] == "keep"
    assert findings[0]["probability"] == 0.93
    assert findings[1]["verdict"] == "rewrite"
    assert findings[1]["probability"] == 0.88
    assert "verdict" not in findings[2]
    assert "probability" not in findings[2]


def test_format_github_folds_verdict_into_message():
    lines = format_github(annotated()).splitlines()
    assert lines[0] == "::error file=a.md,line=3,col=5::em-dash - em dash in prose [keep 0.93]"
    assert lines[1] == "::warning file=a.md,line=4,col=1::semicolon - semi [rewrite 0.88]"
    assert lines[2] == "::warning file=a.md,line=5,col=1::hedge - hedge"


def test_schema_walker_rejects_a_wrong_typed_key():
    schema = _finding_schema()
    good = {"path": "a.md", "line": 1, "col": 1, "tier": "warn", "name": "x", "message": "m"}
    _check_finding(good, schema)
    for bad in ({**good, "line": "1"}, {**good, "line": 0}, {**good, "path": 3},
                {**good, "verdict": "maybe"}, {**good, "probability": 2}, {**good, "extra": 1}):
        with pytest.raises(AssertionError):
            _check_finding(bad, schema)


def test_output_schema_declares_optional_verdict_fields():
    schema = _finding_schema()
    assert schema["properties"]["verdict"]["enum"] == ["keep", "rewrite"]
    prob = schema["properties"]["probability"]
    assert (prob["type"], prob["minimum"], prob["maximum"]) == ("number", 0, 1)
    assert "verdict" not in schema["required"]
    assert "probability" not in schema["required"]


def test_json_output_validates_with_and_without_verdicts():
    schema = _finding_schema()
    for result in (sample(), annotated()):
        for item in json.loads(format_json(result))["findings"]:
            _check_finding(item, schema)


# The attended view: lines of (style, text) parts, which gum draws in one call. The
# styles are space-separated tokens: bold, faint, pill, and the palette's colour names.


def _text(lines):
    return ["".join(text for _style, text in line) for line in lines]


def _view_sample():
    result = LintResult(findings=[
        Finding("a.md", 1, 3, "error", "em-dash", "em dash in prose"),
        Finding("a.md", 2, 2, "warn", "semicolon", "semicolon in prose"),
        Finding("a.md", 3, 2, "warn", "semicolon", "semicolon in prose"),
    ])
    sources = {"a.md": "a — b\nc; d\ne; f\n"}
    return result, sources


def test_lint_view_groups_each_tell_under_its_file_with_a_caret_per_place():
    result, sources = _view_sample()
    text = _text(lint_view(result, sources, linted=3, width=60))
    assert text == [
        "",
        "   deslopper  lint                    3 files, 1 with slop",
        "",
        "  a.md                                 1 error  2 warnings",
        "  " + "─" * 56,
        "  ✖ em-dash",
        "    em dash in prose",
        "      1:3  a — b",
        "             ^",
        "",
        "  ! semicolon  ×2",
        "    semicolon in prose",
        "      2:2  c; d",
        "            ^",
        "      3:2  e; f",
        "            ^",
        "",
        "  " + "─" * 56,
        "  ✖ 1 error   ! 2 warnings",
        "",
    ]


def test_lint_view_styles_the_parts():
    result, sources = _view_sample()
    lines = lint_view(result, sources, linted=3, width=60)
    assert ("pill", " deslopper ") in lines[1]
    assert ("bold accent", "a.md") in lines[3]
    assert ("bold error", "em-dash") in lines[5]
    assert lines[6][-1] == ("muted", "em dash in prose")
    # The caught text is bold in its tier colour; the rest of the line is muted.
    assert ("bold error", "—") in lines[7] and ("muted", "a ") in lines[7]
    assert lines[8][-1] == ("error", "^")


def test_lint_view_leads_each_row_with_jev_rating():
    result = LintResult(findings=[
        Finding("a.md", 1, 3, "error", "em-dash", "em dash", verdict="keep", probability=0.93),
        Finding("a.md", 2, 2, "warn", "semicolon", "semi", verdict="rewrite", probability=0.71),
        Finding("a.md", 3, 2, "warn", "semicolon", "semi"),
    ])
    sources = {"a.md": "a — b\nc; d\ne; f\n"}
    judged = Triage(result=result, tokens=1577, cost=Decimal("0.000066"))
    text = _text(lint_view(result, sources, linted=1, width=80, judged=judged))
    rows = [line for line in text if ":" in line and line.startswith("      ")]
    assert rows[0] == "      ❚❚❚❚❚ 0.93 keep     1:3  a — b"
    assert rows[1] == "      ❚❚❚❚❚ 0.71 rewrite  2:2  c; d"
    # A place Jev did not answer is padded, so the columns still line up.
    assert rows[2] == "      " + " " * 20 + "3:2  e; f"
    assert "  Jev 1 rewrite  ·  1 keep  ·  1,577 tokens  ·  $0.000066" in text


def test_lint_view_counts_the_cached_answers_beside_the_spend():
    result, sources = _view_sample()
    judged = Triage(result=result, tokens=120, cost=Decimal("0.00001"), cached=3)
    text = _text(lint_view(result, sources, linted=1, width=100, judged=judged))
    assert any(line.endswith("120 tokens  ·  $0.00001  ·  3 cached") for line in text)


def test_lint_view_shows_the_cost_without_trailing_zeros():
    result, sources = _view_sample()
    judged = Triage(result=result, tokens=3820, cost=Decimal("0.000140700"))
    text = _text(lint_view(result, sources, linted=1, width=80, judged=judged))
    assert any(line.endswith("3,820 tokens  ·  $0.0001407") for line in text)


def test_lint_view_puts_a_failed_jev_request_and_an_unreadable_file_in_the_footer():
    result, sources = _view_sample()
    result.unreadable.append("gone.md")
    judged = Triage(result=result, errors=["a.md: gateway returned 500"])
    text = _text(lint_view(result, sources, linted=4, width=60, judged=judged))
    assert "  ↳ cannot read gone.md" in text
    assert "  ✖ Jev skipped a.md: gateway returned 500" in text


def test_lint_view_of_a_clean_run_says_so():
    text = _text(lint_view(LintResult(), {}, linted=2, width=60))
    assert text[1].startswith("   deslopper  lint") and text[1].endswith("2 files, 0 with slop")
    assert text[2:] == ["", "  ✔ no slop found", ""]


def test_lint_view_fits_a_narrow_terminal():
    long = "It is a seamless, robust and significantly faster toolkit for modern teams."
    result = LintResult(findings=[
        Finding("docs/a-long-file-name.md", 1, 30, "warn", "vague-intensifier",
                "vague intensifier with no number behind it", verdict="rewrite", probability=0.95),
    ])
    for width in (100, 60, 50, 40):
        judged = Triage(result=result, tokens=10, cost=Decimal("0.00001"))
        text = _text(lint_view(result, {"docs/a-long-file-name.md": long + "\n"}, linted=1,
                               width=width, judged=judged))
        assert all(len(line) <= width for line in text), (width, max(text, key=len))
        caret = next(line for line in text if line.strip() == "^")
        row = text[text.index(caret) - 1]
        # The caret sits under the first letter of the caught word.
        assert row[caret.index("^"):].startswith("signif")


def test_excerpt_keeps_the_caught_word_and_trims_around_it():
    text = "Acme is a seamless, robust toolkit for modern teams — it just works."
    before, word, after = excerpt(text, 11, 30)
    assert word == "seamless"
    assert len(before) + len(word) + len(after) <= 30
    assert before.endswith("is a ") and after.startswith(", robust")
    assert after.endswith("…")
    # Punctuation that is itself the tell stays the caught word.
    assert excerpt("c; d", 2, 30) == ("c", ";", " d")


def test_rule_lines_align_the_tells():
    from deslopper.rules import compile_tell
    tells = [compile_tell({"name": "em-dash", "tier": "error", "phase": "post-entity",
                           "message": "use a colon", "pattern": "x"}),
             compile_tell({"name": "semicolon", "tier": "warn", "phase": "post-entity",
                           "message": "prefer a full stop", "pattern": "y"})]
    assert _text(rule_lines(tells, width=100)) == [
        "  em-dash    ✖ error  post-entity all  use a colon",
        "  semicolon  ! warn   post-entity all  prefer a full stop",
    ]
