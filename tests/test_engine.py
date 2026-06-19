from deslopper.engine import lint_files
from deslopper.rules import compile_tell


def lint_text(tmp_path, text, tells):
    p = tmp_path / "doc.md"
    p.write_text(text, encoding="utf-8")
    return lint_files([("doc.md", str(p))], tells)


SEMI = {"name": "semicolon", "tier": "warn", "kind": "regex", "pattern": ";", "message": "semi"}
EM_ENTITY = {"name": "em-dash", "tier": "error", "phase": "pre-entity", "kind": "regex",
             "pattern": r"&mdash;|&#0*8212;", "message": "entity"}
EM_LITERAL = {"name": "em-dash", "tier": "error", "kind": "regex",
              "pattern": r"[—―]", "message": "literal"}


def test_reports_column_one_based(tmp_path):
    r = lint_text(tmp_path, "a; b\n", [compile_tell(SEMI)])
    assert [(f.line, f.col, f.tier, f.name) for f in r.findings] == [(1, 2, "warn", "semicolon")]


def test_skips_fenced_code(tmp_path):
    text = "```\n; inside fence\n```\n; outside\n"
    r = lint_text(tmp_path, text, [compile_tell(SEMI)])
    assert [f.line for f in r.findings] == [4]


def test_longer_fence_not_closed_by_shorter_inner_run(tmp_path):
    text = "````\nouter\n```\nstill inside ;\n````\n; outside\n"
    r = lint_text(tmp_path, text, [compile_tell(SEMI)])
    assert [f.line for f in r.findings] == [6]


def test_masks_inline_code(tmp_path):
    r = lint_text(tmp_path, "use `a; b` then ; here\n", [compile_tell(SEMI)])
    assert [f.col for f in r.findings] == [17]


def test_front_matter_skipped_open_first_line_only(tmp_path):
    text = "---\ntitle: a; b\n---\n; body\n"
    r = lint_text(tmp_path, text, [compile_tell(SEMI)])
    assert [f.line for f in r.findings] == [4]


def test_front_matter_closes_on_dots(tmp_path):
    text = "---\ntitle: a; b\n...\n; body\n"
    r = lint_text(tmp_path, text, [compile_tell(SEMI)])
    assert [f.line for f in r.findings] == [4]


def test_dashes_not_first_line_are_not_front_matter(tmp_path):
    text = "# heading\n\n---\n; body\n"
    r = lint_text(tmp_path, text, [compile_tell(SEMI)])
    assert [f.line for f in r.findings] == [4]


def test_disable_line_and_region(tmp_path):
    text = ("; one\n"
            "; two <!-- deslop-lint-disable-line -->\n"
            "<!-- deslop-lint-disable -->\n"
            "; suppressed\n"
            "<!-- deslop-lint-enable -->\n"
            "; four\n")
    r = lint_text(tmp_path, text, [compile_tell(SEMI)])
    assert [f.line for f in r.findings] == [1, 6]


def test_entity_phase_runs_before_entity_mask(tmp_path):
    text = "an &mdash; here and a real — dash\n"
    r = lint_text(tmp_path, text, [compile_tell(EM_ENTITY), compile_tell(EM_LITERAL)])
    msgs = [(f.col, f.message) for f in r.findings]
    assert (4, "entity") in msgs
    assert any(m == "literal" for _, m in msgs)


def test_unreadable_file_is_recorded(tmp_path):
    r = lint_files([("missing.md", str(tmp_path / "nope.md"))], [compile_tell(SEMI)])
    assert r.unreadable == ["missing.md"]
    assert r.findings == []


def test_astral_emoji_counts_as_one_column(tmp_path):
    emoji = {"name": "emoji", "tier": "warn", "kind": "regex",
             "pattern": r"[\U0001F300-\U0001FAFF]", "message": "e"}
    r = lint_text(tmp_path, "ab \U0001F680 ;\n", [compile_tell(emoji), compile_tell(SEMI)])
    # rocket at col 4 (1-based, code points), semicolon after it
    cols = {(f.name, f.col) for f in r.findings}
    assert ("emoji", 4) in cols


def test_mdx_skips_esm_import_export(tmp_path):
    # In .mdx, top-level import/export are ESM statements, not prose. Their
    # semicolons must not be flagged.
    p = tmp_path / "doc.mdx"
    p.write_text("import {Foo} from 'bar';\nexport const x = 1;\n; body\n", encoding="utf-8")
    r = lint_files([("doc.mdx", str(p))], [compile_tell(SEMI)])
    assert [f.line for f in r.findings] == [3]


def test_mdx_lints_prose_inside_jsx(tmp_path):
    # JSX wraps rendered prose, so it is still scanned.
    p = tmp_path / "doc.mdx"
    p.write_text("<Callout>a; b</Callout>\n", encoding="utf-8")
    r = lint_files([("doc.mdx", str(p))], [compile_tell(SEMI)])
    assert [f.line for f in r.findings] == [1]


def test_md_does_not_skip_import_prose(tmp_path):
    # ESM masking is .mdx-only. A .md line that starts with "import" is prose.
    p = tmp_path / "doc.md"
    p.write_text("import the data; then continue\n", encoding="utf-8")
    r = lint_files([("doc.md", str(p))], [compile_tell(SEMI)])
    assert [f.line for f in r.findings] == [1]
