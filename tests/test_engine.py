from deslopper.engine import lint_files, scan_prose
from deslopper.rules import compile_tell


def lint_text(tmp_path, text, tells):
    p = tmp_path / "doc.md"
    p.write_text(text, encoding="utf-8")
    return lint_files([("doc.md", str(p))], tells)


def scan(text, is_mdx=False):
    return list(scan_prose(text.splitlines(keepends=True), is_mdx))


# scan_prose is the seam under lint_file: raw lines in, the prose lines that tells
# actually see out. Testing it directly pins the block-structure and masking rules
# without routing every case through a crafted tell.

def test_scan_prose_yields_only_prose_lines():
    text = ("---\ntitle: a\n---\n"       # front matter, lines 1-3
            "prose one\n"                 # line 4
            "```\nfenced ;\n```\n"        # fence, lines 5-7
            "prose two\n")                # line 8
    assert [(p.lineno, p.pre_entity) for p in scan(text)] == [(4, "prose one"), (8, "prose two")]


def test_scan_prose_masks_inline_code_then_entities():
    (p,) = scan("use `@@@` and &amp; here\n")
    assert p.lineno == 1
    assert "@" not in p.pre_entity            # inline code masked in both phases
    assert "&amp;" in p.pre_entity            # entity still visible pre-entity
    assert "&" not in p.post_entity           # entity masked post-entity
    assert len(p.pre_entity) == len("use `@@@` and &amp; here")   # columns preserved


def test_scan_prose_honours_disable_region():
    text = ("keep one\n"
            "<!-- deslop-lint-disable -->\n"
            "dropped\n"
            "<!-- deslop-lint-enable -->\n"
            "keep two\n")
    assert [p.lineno for p in scan(text)] == [1, 5]


def test_scan_prose_skips_mdx_esm_only_when_mdx():
    text = "import x from 'y';\n; body\n"
    assert [p.lineno for p in scan(text, is_mdx=True)] == [2]
    assert [p.lineno for p in scan(text, is_mdx=False)] == [1, 2]


# Fence handling follows CommonMark's block rules. Each of these used to open or close a
# fence wrongly and silently swallow the rest of the file.

def test_scan_prose_indented_fence_is_not_a_fence():
    # A run indented 4+ spaces is an indented-code line, not a fence opener; it must not
    # start a block that eats everything after it.
    text = "prose a\n    ```\nprose b\n"
    assert [p.lineno for p in scan(text)] == [1, 2, 3]


def test_scan_prose_closer_with_info_string_does_not_close():
    # A closer carries no info string, so ```lang keeps the fence open until a bare ```.
    text = "```\ncode ;\n```lang\nstill code ;\n```\nprose\n"
    assert [p.lineno for p in scan(text)] == [6]


def test_scan_prose_backtick_in_info_string_is_not_a_fence_opener():
    # A backtick fence's info string may not contain a backtick, so this line is prose.
    text = "```js `x`\nprose two\n"
    assert [p.lineno for p in scan(text)] == [1, 2]


def test_scan_prose_disable_suffix_does_not_disable_the_file():
    # An unrecognised directive (eslint's disable-next-line) must not switch on the
    # block-level disable and swallow the rest of the file.
    text = ("keep one\n"
            "<!-- deslop-lint-disable-next-line -->\n"
            "keep two\n")
    assert [p.lineno for p in scan(text)] == [1, 2, 3]


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
