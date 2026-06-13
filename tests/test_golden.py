import os

from deslopper.config import load_config
from deslopper.engine import lint_files
from deslopper import report


def _result(fixtures_dir):
    cfg, _ = load_config(None, fixtures_dir)
    path = os.path.join(fixtures_dir, "comprehensive.md")
    return lint_files([("comprehensive.md", path)], cfg.tells)


def _check(fixtures_dir, name, rendered):
    golden = os.path.join(fixtures_dir, name)
    if not os.path.exists(golden):
        with open(golden, "w", encoding="utf-8") as fh:
            fh.write(rendered)
    with open(golden, encoding="utf-8") as fh:
        assert rendered == fh.read()


def test_golden_text(fixtures_dir):
    _check(fixtures_dir, "comprehensive.text.golden", report.format_text(_result(fixtures_dir)))


def test_golden_github(fixtures_dir):
    _check(fixtures_dir, "comprehensive.github.golden", report.format_github(_result(fixtures_dir)))


def test_golden_json(fixtures_dir):
    _check(fixtures_dir, "comprehensive.json.golden", report.format_json(_result(fixtures_dir)))
