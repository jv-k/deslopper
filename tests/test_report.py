import json

import pytest

from deslopper import ui
from deslopper.findings import Finding, LintResult
from deslopper.report import format_text, format_github, format_json, summary_line, exit_code
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


@pytest.mark.parametrize("score, filled, style", [
    (0.93, 5, "ok"),
    (0.88, 4, "warn"),
    (0.70, 4, "warn"),
    (0.55, 3, "error"),
    (1.0, 5, "ok"),
    (0.0, 0, "error"),
])
def test_rating_bar_fills_by_score_and_colours_by_confidence(score, filled, style):
    pal = ui.Palette(True)
    bar = ui.rating_bar(pal, score)
    assert bar.count(ui.I_BAR) == ui.BAR_SLOTS
    assert bar.startswith(getattr(pal, style) + ui.I_BAR * filled + pal.reset)
    assert bar.endswith(pal.dim + ui.I_BAR * (ui.BAR_SLOTS - filled) + pal.reset)


def test_rating_bar_is_plain_glyphs_when_the_gate_is_off():
    assert ui.rating_bar(ui.PLAIN, 0.88) == ui.I_BAR * ui.BAR_SLOTS


def test_format_text_styled_leads_with_the_rating_bar_and_keeps_the_verdict_tail():
    pal = ui.Palette(True)
    lines = format_text(annotated(), pal).splitlines()
    assert lines[0].startswith(f"{ui.rating_bar(pal, 0.93)} {pal.bold}a.md{pal.reset}:3:5 ")
    assert lines[0].endswith(" [keep]")
    assert lines[1].startswith(f"{ui.rating_bar(pal, 0.88)} {pal.bold}a.md{pal.reset}:4:1 ")
    assert lines[1].endswith(" [rewrite]")
    assert "0.93" not in lines[0] and "0.88" not in lines[1]


def test_format_text_styled_pads_an_unjudged_line_in_a_judged_run():
    pal = ui.Palette(True)
    line = format_text(annotated(), pal).splitlines()[2]
    assert line.startswith(" " * (ui.BAR_SLOTS + 1) + f"{pal.bold}a.md{pal.reset}:5:1 ")
    assert ui.I_BAR not in line
    assert not line.endswith("]")


def test_format_text_styled_has_no_prefix_without_triage():
    pal = ui.Palette(True)
    unjudged = LintResult(findings=[Finding("a.md", 3, 5, "error", "em-dash", "em dash"),
                                    Finding("a.md", 4, 1, "warn", "semicolon", "semi")])
    lines = format_text(unjudged, pal).splitlines()
    assert all(line.startswith(f"{pal.bold}a.md{pal.reset}:") for line in lines)


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
