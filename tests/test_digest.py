"""The protected-content digest the preservation judge compares."""

from deslopper.digest import diff_components, digest_text

DOC = """\
---
title: Sample
---

# Title — loud

Some prose with a [link](https://example.com/a) in it.

| Name | Value |
| ---- | ----- |
| a    | 1     |

## Details

```python
x = "—"  # § stays
```

More prose, another [link](https://example.com/b).
"""


def test_digest_captures_protected_content():
    d = digest_text(DOC)
    assert d.front_matter == "---\ntitle: Sample\n---"
    assert d.headings == ["# Title — loud", "## Details"]
    assert d.fences == ['```python\nx = "—"  # § stays\n```']
    assert d.table_rows == [["Name", "Value"], ["a", "1"]]
    assert d.links == ["https://example.com/a", "https://example.com/b"]


def test_rewording_prose_leaves_the_digest_equal():
    reworded = DOC.replace("Some prose with a", "Prose that keeps a")
    assert digest_text(DOC) == digest_text(reworded)
    assert diff_components(digest_text(DOC), digest_text(reworded)) == []


def test_diff_components_names_what_changed():
    mangled_fence = DOC.replace('x = "—"', 'x = "-"')
    assert diff_components(digest_text(DOC), digest_text(mangled_fence)) == ["fenced code"]

    dropped_link = DOC.replace("(https://example.com/b)", "(https://example.com/c)")
    assert diff_components(digest_text(DOC), digest_text(dropped_link)) == [
        "link destinations"
    ]

    padded_cells = DOC.replace("| a    | 1     |", "|  a | 1 |")
    assert diff_components(digest_text(DOC), digest_text(padded_cells)) == []
