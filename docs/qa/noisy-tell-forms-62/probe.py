"""Count line hits for the hidden-truth, mic-drop and negation-pivot tells (issue #62).

Run from the repo root after fetching the corpora (see README.md beside this file):

    .venv/bin/python docs/qa/noisy-tell-forms-62/probe.py

Each tell is split into its top-level alternation branches, so the count shows which
form fires. A line counts once per branch. Lines go through the same matcher the
linter uses, one line at a time.
"""
from pathlib import Path

from deslopper.presets import load_builtin
from deslopper.rules import compile_tell

HERE = Path(__file__).resolve().parent
CORPORA = {
    "Django 3.2 docs (docs/**/*.txt)": (HERE / "corpus/django-3.2.25/docs", "*.txt"),
    "CPython 3.9 docs (Doc/**/*.rst)": (HERE / "corpus/cpython-3.9.0/Doc", "*.rst"),
}
NAMES = ["hidden-truth", "mic-drop", "negation-pivot"]


def branches(pattern):
    """Split a regex on its top-level | only, skipping escapes and character classes."""
    found, group_depth, current, pos = [], 0, "", 0
    in_class = False
    while pos < len(pattern):
        char = pattern[pos]
        if char == "\\":
            current += pattern[pos:pos + 2]
            pos += 2
            continue
        if in_class:
            in_class = char != "]"
        elif char == "[":
            in_class = True
        elif char == "(":
            group_depth += 1
        elif char == ")":
            group_depth -= 1
        elif char == "|" and group_depth == 0:
            found.append(current)
            current = ""
            pos += 1
            continue
        current += char
        pos += 1
    found.append(current)
    return found


def main():
    preset = "recommended"
    tells = {t["name"]: t for t in load_builtin(preset)["tells"] if t["name"] in NAMES}
    for label, (root, glob) in CORPORA.items():
        lines = [(p, n, line.rstrip("\n"))
                 for p in sorted(root.rglob(glob))
                 for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace")
                                          .splitlines(True), 1)]
        print(f"## {label}: {len(lines)} lines, preset {preset}\n")
        for name in NAMES:
            if name not in tells:
                continue
            raw = tells[name]
            whole = compile_tell(raw)
            total = sum(1 for _, _, t in lines if list(whole.matcher(t)))
            print(f"{name}: {total} lines")
            for b in branches(raw["pattern"]):
                tell = compile_tell({**raw, "pattern": b})
                hits = [(p, n, t, offs) for p, n, t in lines if (offs := list(tell.matcher(t)))]
                print(f"  branch {b!r}: {len(hits)}")
                for p, n, t, offs in hits:
                    print(f"    {p.relative_to(root)}:{n}:{offs[0] + 1}: {t.strip()[:110]}")
            print()


if __name__ == "__main__":
    main()
