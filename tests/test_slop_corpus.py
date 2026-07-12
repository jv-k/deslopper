"""Regression test: the linter must flag realistic AI-generated slop.

`ai_slop.md` is a natural-reading marketing/blog post of the kind LLMs
actually emit. Every prose-level tell in the recommended preset should fire
on it. (The HTML-entity tells -- em-dash/section-sign as &mdash;/&sect; --
are not natural in rendered prose and are covered by comprehensive.md.)
"""

import collections
import os

from deslopper.config import load_config
from deslopper.engine import lint_files

PROSE_TELLS = {
    "em-dash",
    "middle-dot",
    "semicolon",
    "bold-bullet-lead",
    "not-just-x-but-y",
    "filler-verb",
    "marketing-adjective",
    "throat-clearing",
    "vague-intensifier",
    "emoji",
}


def _findings(fixtures_dir):
    cfg, _ = load_config(None, fixtures_dir)
    path = os.path.join(fixtures_dir, "ai_slop.md")
    return lint_files([("ai_slop.md", path)], cfg.tells).findings


def test_every_prose_tell_fires_on_ai_slop(fixtures_dir):
    fired = {f.name for f in _findings(fixtures_dir)}
    missing = PROSE_TELLS - fired
    assert not missing, f"these prose tells failed to flag known slop: {sorted(missing)}"


def test_slop_corpus_reports_an_error_and_many_warnings(fixtures_dir):
    counts = collections.Counter(f.tier for f in _findings(fixtures_dir))
    assert counts["error"] >= 1
    assert counts["warn"] >= 20
