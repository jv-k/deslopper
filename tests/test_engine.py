from deslopper.engine import Dialect, dialect_for, lint_files, scan_prose
from deslopper.rules import compile_tell


def lint_text(tmp_path, text, tells):
    p = tmp_path / "doc.md"
    p.write_text(text, encoding="utf-8")
    return lint_files([("doc.md", str(p))], tells)


def scan(text, is_mdx=False, dialect=None):
    if dialect is None:
        dialect = Dialect.MDX if is_mdx else Dialect.MARKDOWN
    return list(scan_prose(text.splitlines(keepends=True), dialect))


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


# The dialect is the one place the scanner learns the file type. The runner picks it
# from the display path's extension.

def test_dialect_for_maps_extension():
    assert dialect_for("doc.mdx") is Dialect.MDX
    assert dialect_for("src/pages/index.astro") is Dialect.ASTRO
    assert dialect_for("README.md") is Dialect.MARKDOWN
    assert dialect_for("notes.markdown") is Dialect.MARKDOWN
    assert dialect_for("notes.txt") is Dialect.MARKDOWN
    assert dialect_for("no-extension") is Dialect.MARKDOWN


def test_dialect_has_exactly_three_cases():
    assert {d.name for d in Dialect} == {"MARKDOWN", "MDX", "ASTRO"}


def test_scan_prose_defaults_to_markdown():
    text = "import x from 'y';\n"
    assert [p.lineno for p in scan_prose(text.splitlines(keepends=True))] == [1]


def test_scan_prose_skips_front_matter_in_markdown_and_mdx():
    for dialect in (Dialect.MARKDOWN, Dialect.MDX):
        for close in ("---", "..."):
            text = f"---\ntitle: a;\n{close}\nbody;\n"
            assert [p.lineno for p in scan(text, dialect=dialect)] == [4], (dialect, close)


def test_scan_prose_astro_markup_reads_like_markdown():
    # After the fence, Astro markup goes through the Markdown path: an import line there
    # is prose, the same as in Markdown.
    text = "---\nimport A from './a';\n---\nimport the data; then go\n"
    assert [p.lineno for p in scan(text, dialect=Dialect.ASTRO)] == [4]
    assert [p.lineno for p in scan(text, dialect=Dialect.ASTRO)] == \
        [p.lineno for p in scan(text, dialect=Dialect.MARKDOWN)]


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


def test_scan_prose_disable_line_suffix_is_not_a_directive():
    # A -disable-line suffix is not the -disable-line directive, so it suppresses nothing.
    text = ("keep one\n"
            "keep two <!-- deslop-lint-disable-line-foo -->\n")
    assert [p.lineno for p in scan(text)] == [1, 2]


def test_scan_prose_backtick_run_pairs_only_with_equal_length():
    # A 2-backtick opener has no equal-length closer here (``` is a 3-run), so nothing is
    # masked as code and the semicolon stays visible as prose.
    (p,) = scan("`` ; ``` x\n")
    assert ";" in p.post_entity


def test_scan_prose_equal_length_backticks_still_mask():
    # Guard against over-relaxing: a real ``...`` span is still masked.
    (p,) = scan("a ``x; y`` b ;\n")
    assert p.post_entity.count(";") == 1     # the span's ; is masked, the trailing ; is not


def test_shorter_opener_does_not_mask_following_prose(tmp_path):
    r = lint_text(tmp_path, "`` ; ``` x\n", [compile_tell(SEMI)])
    assert [f.line for f in r.smells] == [1]   # the ; is seen, not swallowed as code


SEMI = {"name": "semicolon", "tier": "warn", "kind": "regex", "pattern": ";", "message": "semi"}
EM_ENTITY = {"name": "em-dash", "tier": "error", "phase": "pre-entity", "kind": "regex",
             "pattern": r"&mdash;|&#0*8212;", "message": "entity"}
EM_LITERAL = {"name": "em-dash", "tier": "error", "kind": "regex",
              "pattern": r"[—―]", "message": "literal"}


def test_reports_column_one_based(tmp_path):
    r = lint_text(tmp_path, "a; b\n", [compile_tell(SEMI)])
    assert [(f.line, f.col, f.tier, f.name) for f in r.smells] == [(1, 2, "warn", "semicolon")]


def test_skips_fenced_code(tmp_path):
    text = "```\n; inside fence\n```\n; outside\n"
    r = lint_text(tmp_path, text, [compile_tell(SEMI)])
    assert [f.line for f in r.smells] == [4]


def test_longer_fence_not_closed_by_shorter_inner_run(tmp_path):
    text = "````\nouter\n```\nstill inside ;\n````\n; outside\n"
    r = lint_text(tmp_path, text, [compile_tell(SEMI)])
    assert [f.line for f in r.smells] == [6]


def test_masks_inline_code(tmp_path):
    r = lint_text(tmp_path, "use `a; b` then ; here\n", [compile_tell(SEMI)])
    assert [f.col for f in r.smells] == [17]


def test_front_matter_skipped_open_first_line_only(tmp_path):
    text = "---\ntitle: a; b\n---\n; body\n"
    r = lint_text(tmp_path, text, [compile_tell(SEMI)])
    assert [f.line for f in r.smells] == [4]


def test_front_matter_closes_on_dots(tmp_path):
    text = "---\ntitle: a; b\n...\n; body\n"
    r = lint_text(tmp_path, text, [compile_tell(SEMI)])
    assert [f.line for f in r.smells] == [4]


def test_dashes_not_first_line_are_not_front_matter(tmp_path):
    text = "# heading\n\n---\n; body\n"
    r = lint_text(tmp_path, text, [compile_tell(SEMI)])
    assert [f.line for f in r.smells] == [4]


def test_disable_line_and_region(tmp_path):
    text = ("; one\n"
            "; two <!-- deslop-lint-disable-line -->\n"
            "<!-- deslop-lint-disable -->\n"
            "; suppressed\n"
            "<!-- deslop-lint-enable -->\n"
            "; four\n")
    r = lint_text(tmp_path, text, [compile_tell(SEMI)])
    assert [f.line for f in r.smells] == [1, 6]


def test_entity_phase_runs_before_entity_mask(tmp_path):
    text = "an &mdash; here and a real — dash\n"
    r = lint_text(tmp_path, text, [compile_tell(EM_ENTITY), compile_tell(EM_LITERAL)])
    msgs = [(f.col, f.message) for f in r.smells]
    assert (4, "entity") in msgs
    assert any(m == "literal" for _, m in msgs)


def test_unreadable_file_is_recorded(tmp_path):
    r = lint_files([("missing.md", str(tmp_path / "nope.md"))], [compile_tell(SEMI)])
    assert r.unreadable == ["missing.md"]
    assert r.smells == []


def test_astral_emoji_counts_as_one_column(tmp_path):
    emoji = {"name": "emoji", "tier": "warn", "kind": "regex",
             "pattern": r"[\U0001F300-\U0001FAFF]", "message": "e"}
    r = lint_text(tmp_path, "ab \U0001F680 ;\n", [compile_tell(emoji), compile_tell(SEMI)])
    # rocket at col 4 (1-based, code points), semicolon after it
    cols = {(f.name, f.col) for f in r.smells}
    assert ("emoji", 4) in cols


def test_mdx_skips_esm_import_export(tmp_path):
    # In .mdx, top-level import/export are ESM statements, not prose. Their
    # semicolons must not be flagged.
    p = tmp_path / "doc.mdx"
    p.write_text("import {Foo} from 'bar';\nexport const x = 1;\n; body\n", encoding="utf-8")
    r = lint_files([("doc.mdx", str(p))], [compile_tell(SEMI)])
    assert [f.line for f in r.smells] == [3]


def test_mdx_lints_prose_inside_jsx(tmp_path):
    # JSX wraps rendered prose, so it is still scanned.
    p = tmp_path / "doc.mdx"
    p.write_text("<Callout>a; b</Callout>\n", encoding="utf-8")
    r = lint_files([("doc.mdx", str(p))], [compile_tell(SEMI)])
    assert [f.line for f in r.smells] == [1]


def test_md_does_not_skip_import_prose(tmp_path):
    # ESM masking is .mdx-only. A .md line that starts with "import" is prose.
    p = tmp_path / "doc.md"
    p.write_text("import the data; then continue\n", encoding="utf-8")
    r = lint_files([("doc.md", str(p))], [compile_tell(SEMI)])
    assert [f.line for f in r.smells] == [1]


def test_lint_files_picks_dialect_from_display_path(tmp_path):
    # The read path has no extension; the display path decides the dialect.
    text = "---\ntitle: a;\n...\nimport x from 'y';\n; body\n"
    p = tmp_path / "blob"
    p.write_text(text, encoding="utf-8")
    lines = {name: [f.line for f in lint_files([(name, str(p))], [compile_tell(SEMI)]).smells]
             for name in ("doc.md", "doc.mdx", "page.astro")}
    # In .astro the `...` does not close the fence, so every later line is fence code.
    assert lines == {"doc.md": [4, 5], "doc.mdx": [5], "page.astro": []}


# An .astro file's first-line `---` opens a code fence. Only the text inside its string
# literals is prose; the code around them is masked, so a column is the source column.

def lint_astro(tmp_path, text, tells):
    p = tmp_path / "Page.astro"
    p.write_text(text, encoding="utf-8")
    r = lint_files([("Page.astro", str(p))], tells)
    return [(f.line, f.col, f.name) for f in r.smells]


def test_astro_single_quoted_literal_reports_source_column(tmp_path):
    text = "---\nconst T = 'a; b';\n---\n"
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == [(2, 13, "semicolon")]


def test_astro_double_quoted_literal_reports_source_column(tmp_path):
    text = '---\nconst T = "a; b";\n---\n'
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == [(2, 13, "semicolon")]


def test_astro_code_outside_literals_raises_nothing(tmp_path):
    text = ("---\n"
            "const f = (a) => { return a; };\n"
            "let n = 1; n++; if (n > 0 && n !== 2) { n -= 1; }\n"
            "---\n")
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == []


def test_astro_escaped_quote_stays_inside_the_literal(tmp_path):
    text = "---\nconst T = 'don\\'t; stop';\n---\n"
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == [(2, 18, "semicolon")]


def test_astro_unclosed_quote_ends_at_the_line_end(tmp_path):
    text = "---\nconst T = 'open; here\nconst U = 1;\n---\n"
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == [(2, 16, "semicolon")]


def test_astro_import_line_skipped_and_export_const_scanned(tmp_path):
    text = ("---\n"
            "import Card from '../a;b.astro';\n"
            "export const T = 'a; b';\n"
            "---\n")
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == [(3, 20, "semicolon")]


def test_astro_import_meta_and_dynamic_import_lines_are_scanned(tmp_path):
    # Only an import statement is skipped. `import.meta` and `import(` start expressions
    # whose literals are copy like any other.
    text = ("---\n"
            "import.meta.env.X ?? 'a; b';\n"
            "import('./a;b').then(() => 'c; d');\n"
            "---\n")
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == \
        [(2, 24, "semicolon"), (3, 12, "semicolon"), (3, 30, "semicolon")]


def test_astro_warn_tier_tell_fires_on_a_fence_literal(tmp_path):
    p = tmp_path / "Page.astro"
    p.write_text("---\nconst T = 'a; b';\n---\n", encoding="utf-8")
    smells = lint_files([("Page.astro", str(p))], [compile_tell(SEMI)]).smells
    assert [(f.line, f.tier) for f in smells] == [(2, "warn")]


def test_astro_fence_closes_on_dashes_not_dots(tmp_path):
    text = ("---\n"
            "const A = 'a; b';\n"
            "...\n"
            "const B = 'c; d';\n"
            "---\n"
            "; body\n")
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == \
        [(2, 13, "semicolon"), (4, 13, "semicolon"), (6, 1, "semicolon")]


def test_astro_dashes_after_line_one_are_not_a_fence(tmp_path):
    text = "# heading\n---\n; body\nconst T = 'a';\n---\n"
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == \
        [(3, 1, "semicolon"), (4, 14, "semicolon")]


def test_astro_both_entity_phases_apply_to_fence_literals(tmp_path):
    mdash_word = {"name": "mdash-word", "tier": "warn", "kind": "regex",
                  "pattern": "mdash", "message": "post"}
    text = "---\nconst T = 'a &mdash; b — c';\n---\n"
    tells = [compile_tell(EM_ENTITY), compile_tell(EM_LITERAL), compile_tell(mdash_word)]
    # The pre-entity tell sees the entity; the post-entity tells see it masked.
    assert lint_astro(tmp_path, text, tells) == [(2, 14, "em-dash"), (2, 24, "em-dash")]


def test_astro_fence_lines_get_no_inline_code_masking(tmp_path):
    text = "---\nconst T = 'a `x;` b';\n---\n"
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == [(2, 16, "semicolon")]


def test_astro_markup_after_fence_reports_as_before(tmp_path):
    markup = "\n<p>a; b</p>\n`c;` and d;\n"
    astro = lint_astro(tmp_path, "---\nconst A = 1;\n---\n" + markup, [compile_tell(SEMI)])
    md = lint_text(tmp_path, "---\ntitle: x\n---\n" + markup, [compile_tell(SEMI)])
    assert astro == [(f.line, f.col, f.name) for f in md.smells] == \
        [(5, 5, "semicolon"), (6, 11, "semicolon")]


def test_md_and_mdx_still_skip_the_same_fence_as_front_matter(tmp_path):
    text = "---\nconst T = 'a; b';\n---\n; body\n"
    p = tmp_path / "blob"
    p.write_text(text, encoding="utf-8")
    for name in ("doc.md", "doc.mdx"):
        smells = lint_files([(name, str(p))], [compile_tell(SEMI)]).smells
        assert [(f.line, f.col) for f in smells] == [(4, 1)], name


# Comments in the fence are code: masked whole, with no literal opened inside them.

def test_astro_line_comment_raises_nothing(tmp_path):
    text = "---\n// a note; with a dash — here\nconst A = 1; // why; it's — so\n---\n"
    tells = [compile_tell(SEMI), compile_tell(EM_LITERAL)]
    assert lint_astro(tmp_path, text, tells) == []


def test_astro_block_comment_on_one_line_raises_nothing(tmp_path):
    text = "---\nconst A = /* a; b — c */ 1;\n---\n"
    tells = [compile_tell(SEMI), compile_tell(EM_LITERAL)]
    assert lint_astro(tmp_path, text, tells) == []


def test_astro_block_comment_across_lines_raises_nothing(tmp_path):
    text = ("---\n"
            "/**\n"
            " * The tagline; it's shown — on the home page.\n"
            " */\n"
            "const T = 'a; b';\n"
            "---\n")
    assert lint_astro(tmp_path, text, [compile_tell(SEMI), compile_tell(EM_LITERAL)]) == \
        [(5, 13, "semicolon")]


def test_astro_quote_in_a_comment_opens_no_literal(tmp_path):
    text = ("---\n"
            "// it's a note; ok\n"
            "/* don't; stop\n"
            "   it's; here */\n"
            "const T = 'a; b';\n"
            "---\n")
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == [(5, 13, "semicolon")]


def test_astro_literal_after_a_closed_block_comment_keeps_its_column(tmp_path):
    text = "---\n/* it's; */ const T = 'b; c';\n---\n"
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == [(2, 25, "semicolon")]


def test_astro_comment_markers_inside_a_literal_are_text(tmp_path):
    text = "---\nconst U = 'https://a; /* b; */';\n---\n"
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == \
        [(2, 21, "semicolon"), (2, 27, "semicolon")]


def test_astro_typescript_annotation_masked_and_literal_type_scanned(tmp_path):
    text = ("---\n"
            "interface Props { title: string; tone?: 'calm; plain' | \"loud\"; }\n"
            "const { title }: Props = Astro.props;\n"
            "---\n")
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == [(2, 46, "semicolon")]


def test_astro_block_comment_opened_on_an_import_line_still_masks(tmp_path):
    # The import line is skipped, but the comment it opens still runs to its closer.
    text = ("---\n"
            "import A from './a'; /* the card\n"
            "   it's; reused */\n"
            "const T = 'a; b';\n"
            "---\n")
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == [(4, 13, "semicolon")]


# A backtick in the fence opens a template literal. Its text is scanned, on every line it
# spans, and each `${...}` interpolation in it is masked up to its matching brace.

def test_astro_template_literal_reports_source_column(tmp_path):
    text = "---\nconst T = `a; b`;\n---\n"
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == [(2, 13, "semicolon")]


def test_astro_template_literal_across_lines_reports_on_each_line(tmp_path):
    text = ("---\n"
            "const T = `first; line\n"
            "plain middle line\n"
            "  last — line; end`;\n"
            "const U = 1;\n"
            "---\n")
    tells = [compile_tell(SEMI), compile_tell(EM_LITERAL)]
    assert lint_astro(tmp_path, text, tells) == \
        [(2, 17, "semicolon"), (4, 8, "em-dash"), (4, 14, "semicolon")]


def test_astro_interpolation_code_raises_nothing(tmp_path):
    text = ("---\n"
            "const T = `a ${f({ k: 'x; y', n: `p; ${q} — r` })} b`;\n"
            "const U = `${ { a: 1; } }`;\n"
            "---\n")
    tells = [compile_tell(SEMI), compile_tell(EM_LITERAL)]
    assert lint_astro(tmp_path, text, tells) == []


def test_astro_template_text_after_a_closed_interpolation_is_scanned(tmp_path):
    text = "---\nconst T = `a ${ {b: 1}.b } c; d`;\n---\n"
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == [(2, 29, "semicolon")]


def test_astro_interpolation_across_lines_stays_masked(tmp_path):
    text = ("---\n"
            "const T = `a ${items.map((i) => {\n"
            "  return 'x; y';\n"
            "})} tail; end`;\n"
            "---\n")
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == [(4, 9, "semicolon")]


def test_astro_escaped_backtick_and_dollar_stay_template_text(tmp_path):
    text = "---\nconst T = `a \\` b; \\${c; d}`;\n---\n"
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == \
        [(2, 18, "semicolon"), (2, 24, "semicolon")]


def test_astro_template_line_starting_with_import_is_scanned(tmp_path):
    # A line inside a template literal is text, even when it starts with `import`.
    text = "---\nconst T = `a\nimport; this too`;\n---\n"
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == [(3, 7, "semicolon")]


# In the fence the exemption directives are written as JS comments, with the same exact
# words as the HTML-comment forms. A region opened in the fence ends at the fence close.

def test_astro_line_comment_disable_line_exempts_its_line(tmp_path):
    text = ("---\n"
            "const A = 'a; b'; // deslop-lint-disable-line\n"
            "const B = 'c; d';\n"
            "---\n")
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == [(3, 13, "semicolon")]


def test_astro_block_comment_region_exempts_until_enable(tmp_path):
    text = ("---\n"
            "/* deslop-lint-disable */\n"
            "const A = 'a; b';\n"
            "const B = `c — d`;\n"
            "/* deslop-lint-enable */\n"
            "const C = 'e; f';\n"
            "---\n")
    tells = [compile_tell(SEMI), compile_tell(EM_LITERAL)]
    assert lint_astro(tmp_path, text, tells) == [(6, 13, "semicolon")]


def test_astro_region_left_open_ends_at_the_fence_close(tmp_path):
    text = ("---\n"
            "/* deslop-lint-disable */\n"
            "const A = 'a; b';\n"
            "---\n"
            "<p>c; d</p>\n")
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == [(5, 5, "semicolon")]


def test_astro_directive_with_unknown_suffix_exempts_nothing(tmp_path):
    text = ("---\n"
            "const A = 'a; b'; // deslop-lint-disable-line-foo\n"
            "/* deslop-lint-disable-next-line */\n"
            "const B = 'c; d';\n"
            "/* deslop-lint-enabled */\n"
            "---\n")
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == \
        [(2, 13, "semicolon"), (4, 13, "semicolon")]


def test_astro_directive_word_inside_a_literal_is_not_a_directive(tmp_path):
    text = "---\nconst A = 'a; // deslop-lint-disable-line';\n---\n"
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == [(2, 13, "semicolon")]


def test_astro_html_directives_in_markup_after_the_fence_still_exempt(tmp_path):
    text = ("---\n"
            "const A = 1; // deslop-lint-disable-line\n"
            "---\n"
            "<p>a; b</p> <!-- deslop-lint-disable-line -->\n"
            "<!-- deslop-lint-disable -->\n"
            "<p>c; d</p>\n"
            "<!-- deslop-lint-enable -->\n"
            "<p>e; f</p>\n")
    assert lint_astro(tmp_path, text, [compile_tell(SEMI)]) == [(8, 5, "semicolon")]
