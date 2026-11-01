# Corpus check for hidden-truth, mic-drop and negation-pivot (issue #62)

Issue #62 asked whether three tells from #60 flag honest prose. This folder holds the probe
and its results.

## Corpora

Both are human technical prose written before chatbot prose was common. The probe reads them
one line at a time, as the linter does.

- The Django 3.2 docs, `docs/**/*.txt` from the 3.2.25 tag: 143,214 lines.
- The CPython 3.9 docs, `Doc/**/*.rst` from the v3.9.0 tag: 262,763 lines.

The corpora are not committed. Fetch them into `corpus/`, which git ignores:

    mkdir -p docs/qa/noisy-tell-forms-62/corpus && cd docs/qa/noisy-tell-forms-62/corpus
    curl -sSL https://github.com/django/django/archive/refs/tags/3.2.25.tar.gz \
      | tar xz django-3.2.25/docs
    curl -sSL https://github.com/python/cpython/archive/refs/tags/v3.9.0.tar.gz \
      | tar xz cpython-3.9.0/Doc

Then run the probe from the repo root with `.venv/bin/python docs/qa/noisy-tell-forms-62/probe.py`.
It prints the line hits for each tell and for each top-level branch of its pattern.

## Results before the change

The counts are lines, per corpus. The named-form columns count the branch that holds the form
the issue names. The whole-tell columns count every branch.

| Tell | Form the issue names | Named form, Django | Named form, CPython | Whole tell, Django | Whole tell, CPython |
| --- | --- | --- | --- | --- | --- |
| `hidden-truth` | `the hard costs of hosting` | 0 | 0 | 0 | 0 |
| `mic-drop` | a bare `It works.` line | 0 | 0 | 0 | 1 |
| `negation-pivot` | `This is not a drill, this is a test.` | 0 | 2 | 0 | 2 |

The `hidden-truth` pattern is one branch, so its two counts are the same.

<!-- deslop-lint-disable -->
The one `mic-drop` hit is on a set-phrase branch that the issue does not name, so it is out
of scope here:

    howto/clinic.rst:1707: (That's the whole point!)

The two `negation-pivot` hits are on the branch that holds the named form, but neither is the
named form itself. Both are honest, and each one leads into an explanation with a colon or a
semicolon:

    library/functions.rst:1471: This is not a bug: it's a result of the fact that most decimal fractions
    reference/simple_stmts.rst:909: That is not a future statement; it's an ordinary import statement with no
<!-- deslop-lint-enable -->

A wider search found no sentence-level `It works.`, `It matters.` or `This shows.` in either
corpus, and no `hard cost` or `hard costs` at all.

## Decisions

- `negation-pivot` is narrowed. The first clause must now end in a full stop or a comma, not
  a colon or a semicolon. The examples from the survey still match, and both CPython lines no
  longer do. After the change the tell has 0 hits in both corpora.
  `tests/test_rules.py` pins the two CPython lines as honest prose.
  The cost is reach: a pivot joined by a colon or a semicolon, such as
  `It's not a bug; it's a feature.`, no longer fires. Moving that form to `aggressive`
  instead would need a new tell name, since `aggressive` may not share a name with a
  `recommended` tell, and new tells are out of scope for #62.
- `hidden-truth` stays as it is. The corpora have no hits, so there is no evidence that it is
  noisy. The issue's `the hard costs of hosting` still matches.
- `mic-drop` stays as it is, for the same reason. A bare `It works.` line still matches.

The issue's `This is not a drill, this is a test.` still matches `negation-pivot`, because a
comma joins its clauses. Neither corpus has a line like it.
