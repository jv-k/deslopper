import json

from deslopper.findings import Finding, LintResult
from deslopper.report import format_text, format_github, format_json, summary_line, exit_code


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
