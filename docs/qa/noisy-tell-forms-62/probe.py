"""Count line hits for the hidden-truth, mic-drop and negation-pivot tells (issue #62).

Run from the repo root after fetching the corpora (see README.md beside this file):

    python3 docs/qa/noisy-tell-forms-62/probe.py [recommended|aggressive]

Each tell is split into its top-level alternation branches, so the count shows which
form fires. A line counts once per branch. Lines go through the same matcher the
linter uses, one line at a time.
"""
import re
import sys
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
    """Split a regex on its top-level | only."""
    out, depth, cur, i = [], 0, "", 0
    while i < len(pattern):
        c = pattern[i]
        if c == "\\":
            cur += pattern[i:i + 2]
            i += 2
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == "|" and depth == 0:
            out.append(cur)
            cur = ""
            i += 1
            continue
        cur += c
        i += 1
    out.append(cur)
    return out


def main():
    preset = sys.argv[1] if len(sys.argv) > 1 else "recommended"
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
                hits = [(p, n, t) for p, n, t in lines if list(tell.matcher(t))]
                print(f"  branch {b!r}: {len(hits)}")
                for p, n, t in hits:
                    m = re.search(b, t, re.I)
                    print(f"    {p.relative_to(root)}:{n}: {m.group(0)!r} | {t.strip()[:110]}")
            print()


if __name__ == "__main__":
    main()
