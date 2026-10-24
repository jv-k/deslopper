"""Throwaway prototypes of deslopper's terminal output, to choose a design from.

Each design draws the same captured run (sample.json: real findings and real Jev
verdicts) as a gum template and renders it with `gum format`, the way deslopper
would, so anything shown here is buildable.

    python3 designs.py <1|2|5|8> [--jev] [--width N] [--from run.json]

Or try them all on a real run with try.sh, which lints once and draws every design.
"""

import json
import os
import subprocess
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))

ERR = "#ff5f87"
WARN = "#ffaf5f"
OK = "#87d787"
ACCENT = "#87afff"
MUTED = "#8a8a8a"
RULE = "#444444"


# Template parts. A JSON string is a valid Go template string, so text stays literal.
def lit(text):
    return "{{ %s }}" % json.dumps(text, ensure_ascii=False)


def fg(colour, text):
    return '{{ Color "%s" %s }}' % (colour, json.dumps(text, ensure_ascii=False))


def bold(text):
    return "{{ Bold %s }}" % json.dumps(text, ensure_ascii=False)


def bold_fg(colour, text):
    return '{{ Bold (Color "%s" %s) }}' % (colour, json.dumps(text, ensure_ascii=False))


def faint(text):
    return "{{ Faint %s }}" % json.dumps(text, ensure_ascii=False)


def pill(colour, text):
    return '{{ Bold (Color "#1c1c1c" "%s" %s) }}' % (colour, json.dumps(f" {text} ", ensure_ascii=False))


def render(lines):
    template = "\n".join(lines) + "\n"
    out = subprocess.run(["gum", "format", "--type", "template"], input=template,
                         capture_output=True, text=True,
                         env={**os.environ, "CLICOLOR_FORCE": "1"})
    sys.stdout.write(out.stdout.rstrip("\n") + "\n" + out.stderr)


# ---------------------------------------------------------------------------------------
# Data


def _root():
    """Where deslopper's display paths start: the git top level, else the current folder."""
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else os.getcwd()


def load(jev, source=None):
    """The captured sample, or a real run's json (`deslopper lint --format json`)."""
    if source is None:
        d = json.load(open(os.path.join(HERE, "sample.json"), encoding="utf-8"))
    else:
        d = json.load(open(source, encoding="utf-8"))
        root = _root()
        d["sources"] = {}
        for path in {f["path"] for f in d["findings"]}:
            try:
                with open(os.path.join(root, path), encoding="utf-8") as fh:
                    d["sources"][path] = fh.read()
            except OSError:
                d["sources"][path] = ""
        jev = jev or "jev" in d
    findings = d["findings"]
    if not jev:
        findings = [{k: v for k, v in f.items() if k not in ("verdict", "probability")}
                    for f in findings]
    files = {}
    for f in findings:
        files.setdefault(f["path"], []).append(f)
    return d, files, jev


def loc_width(files):
    """One location width for the whole run, so the column lines up across files."""
    return max(len(f"{f['line']}:{f['col']}") for fs in files.values() for f in fs)


def msg_indent(full, width):
    """Hang the message under the tell while it has room; on a narrow terminal, start it
    near the left edge instead of squeezing it into a thin column."""
    return full if width - full >= 44 else 6


def flagged(text, col):
    """The flagged word at `col`: from the column to the next space, without trailing
    punctuation, at most 24 characters."""
    rest = text[col - 1:]
    end = rest.find(" ")
    word = rest if end == -1 else rest[:end]
    # Trailing punctuation is not part of the tell, unless the tell is the punctuation.
    word = word.rstrip(".,;:!?\"')") or word
    return word[:24] or rest[:1]


def counts(fs):
    e = sum(f["tier"] == "error" for f in fs)
    w = len(fs) - e
    return e, w


def plural(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def rating(f, width=5):
    """The bar, the probability, and the verdict, as template parts and visible width."""
    if "verdict" not in f:
        return "", 0
    p = f["probability"]
    filled = round(p * width)
    colour = OK if p >= 0.9 else WARN if p >= 0.7 else ERR
    parts = fg(colour, "❚" * filled) + fg(RULE, "❚" * (width - filled))
    verdict = f["verdict"]
    parts += lit(f" {p:.2f} ") + (bold(verdict) if verdict == "rewrite" else faint(verdict))
    parts += lit(" " * (7 - len(verdict)))
    return parts, width + 6 + 7


RATING_W = 5 + 6 + 7


def tier_mark(tier):
    return fg(ERR, "✖") if tier == "error" else fg(WARN, "!")


def tier_colour(tier):
    return ERR if tier == "error" else WARN


def header(d, width, jev):
    files_with = len({f["path"] for f in d["findings"]})
    if "linted" in d:
        right = f"{plural(len(d['linted']), 'file')}, {files_with} with slop"
    else:
        right = f"{plural(files_with, 'file')} with slop"
    left_vis = len(" deslopper ") + 1 + len("lint")
    gap = max(width - 2 - left_vis - len(right), 2)
    line = lit("  ") + pill(ACCENT, "deslopper") + lit(" ") + bold("lint") + lit(" " * gap) + faint(right)
    out = ["", line]
    if jev:
        out.append(lit("  ") + faint("Jev read " + plural(len(d["findings"]), "finding")
                                     + f" in {files_with} files"))
    return out + [""]


def footer(d, width, jev, rule=True):
    e, w = d["summary"]["errors"], d["summary"]["warnings"]
    out = []
    if rule:
        out.append(lit("  ") + fg(RULE, "─" * (width - 4)))
    status = fg(ERR, "✖ ") + bold_fg(ERR, plural(e, "error")) if e else fg(OK, "✔ no errors")
    line = lit("  ") + status + lit("   ") + fg(WARN, "! ") + bold_fg(WARN, plural(w, "warning"))
    out.append(line)
    if jev:
        j = d["jev"]
        verdicts = lit("  ") + fg(ACCENT, "Jev ") + lit(f"{j['rewrite']} rewrite") + faint("  ·  ") + lit(f"{j['keep']} keep")
        spend = f"{j['tokens']:,} tokens  ·  ${float(j['cost']):.5f}"
        verdicts_vis = 6 + len(f"{j['rewrite']} rewrite") + 5 + len(f"{j['keep']} keep")
        if verdicts_vis + 5 + len(spend) <= width:
            out.append(verdicts + faint("  ·  " + spend))
        else:
            out += [verdicts, lit("      ") + faint(spend)]
    return out + [""]


# ---------------------------------------------------------------------------------------
# 1. Ledger: a section per file with a rule and counts; two-line entries.


def ledger(d, files, width, jev):
    lines = header(d, width, jev)
    for path, fs in files.items():
        e, w = counts(fs)
        tally = (fg(ERR, plural(e, "error")) + lit("  ") if e else "") + fg(WARN, plural(w, "warning"))
        tally_vis = (len(plural(e, "error")) + 2 if e else 0) + len(plural(w, "warning"))
        gap = max(width - 4 - len(path) - tally_vis, 2)
        lines.append(lit("  ") + bold_fg(ACCENT, path) + lit(" " * gap) + tally)
        lines.append(lit("  ") + fg(RULE, "─" * (width - 4)))
        loc_w = loc_width(files)
        for f in fs:
            loc = f"{f['line']}:{f['col']}".rjust(loc_w)
            r, _ = rating(f)
            lead = (r + lit("   ")) if r else ""
            lead_w = (RATING_W + 3) if r else 0
            lines.append(lit("  ") + lead + faint(loc) + lit("  ") + tier_mark(f["tier"]) + lit(" ")
                         + bold(f["name"]))
            indent = msg_indent(2 + lead_w + loc_w + 2 + 2, width)
            for part in textwrap.wrap(f["message"], width - indent - 2):
                lines.append(lit(" " * indent) + fg(MUTED, part))
        lines.append("")
    return lines + footer(d, width, jev)


# ---------------------------------------------------------------------------------------
# 2. Snippet: each finding shows its source line with the match underlined.


def _excerpt(text, col, room):
    """The source line cut to `room` characters around column `col`, and the new col."""
    if len(text) <= room:
        return text, col
    start = max(0, min(col - 1 - room // 3, len(text) - room))
    cut = text[start:start + room]
    if start > 0:
        cut = "…" + cut[1:]
    if start + room < len(text):
        cut = cut[:-1] + "…"
    return cut, col - start


def snippet(d, files, width, jev):
    lines = header(d, width, jev)
    for path, fs in files.items():
        e, w = counts(fs)
        lines.append(lit("  ") + bold_fg(ACCENT, path) + faint(
            f"   {plural(e, 'error')}, {plural(w, 'warning')}" if e else f"   {plural(w, 'warning')}"))
        lines.append("")
        source = d["sources"][path].split("\n")
        num_w = max(len(str(f["line"])) for f in fs)
        for f in fs:
            colour = tier_colour(f["tier"])
            r, _ = rating(f)
            lines.append(lit("  ") + tier_mark(f["tier"]) + lit(" ") + bold_fg(colour, f["name"])
                         + faint(f"  {f['line']}:{f['col']}") + ((lit("    ") + r) if r else ""))
            gutter = " " * (num_w + 3)
            text, col = _excerpt(source[f["line"] - 1], f["col"], width - len(gutter) - 4)
            lines.append(lit(f"  {str(f['line']).rjust(num_w)} ") + fg(RULE, "│ ") + lit(text))
            lines.append(lit(f"  {' ' * num_w} ") + fg(RULE, "│ ") + lit(" " * (col - 1)) + fg(colour, "^"))
            for i, part in enumerate(textwrap.wrap(f["message"], width - len(gutter) - 6)):
                lines.append(lit(f"  {' ' * num_w} ") + fg(RULE, "╰ " if i == 0 else "  ") + fg(MUTED, part))
            lines.append("")
    return lines + footer(d, width, jev)


# ---------------------------------------------------------------------------------------
# 5. Tell first: each tell once per file with its hint, then each place it fired, with the
#    words it caught and, when Jev ran, Jev's rating in front.


def tell_first(d, files, width, jev, caret=False):
    """`caret` adds a line under each row with one ^ under the start of the caught word."""
    lines = header(d, width, jev)
    loc_w = loc_width(files)
    for path, fs in files.items():
        e, w = counts(fs)
        tally = (fg(ERR, plural(e, "error")) + lit("  ") if e else "") + fg(WARN, plural(w, "warning"))
        tally_vis = (len(plural(e, "error")) + 2 if e else 0) + len(plural(w, "warning"))
        lines.append(lit("  ") + bold_fg(ACCENT, path) + lit(" " * max(width - 4 - len(path) - tally_vis, 2)) + tally)
        lines.append(lit("  ") + fg(RULE, "─" * (width - 4)))
        source = d["sources"][path].split("\n")
        groups = {}
        for f in fs:
            groups.setdefault(f["name"], []).append(f)
        ordered = sorted(groups.items(), key=lambda kv: (kv[1][0]["tier"] != "error", kv[1][0]["line"]))
        for i, (name, gs) in enumerate(ordered):
            tier = gs[0]["tier"]
            if i:
                lines.append("")
            lines.append(lit("  ") + tier_mark(tier) + lit(" ") + bold_fg(tier_colour(tier), name)
                         + (faint(f"  ×{len(gs)}") if len(gs) > 1 else ""))
            for part in textwrap.wrap(gs[0]["message"], width - 8):
                lines.append(lit("    ") + fg(MUTED, part))
            for g in gs:
                r, _ = rating(g)
                lead = (r + lit("  ")) if r else ""
                lead_w = (RATING_W + 2) if r else 0
                loc = f"{g['line']}:{g['col']}".rjust(loc_w)
                text = source[g["line"] - 1]
                word = flagged(text, g["col"])
                room = width - 6 - lead_w - loc_w - 2 - 2
                before = text[:g["col"] - 1]
                after = text[g["col"] - 1 + len(word):]
                keep_before = max(room // 3, room - len(word) - len(after))
                if len(before) > keep_before:
                    before = "…" + before[-(keep_before - 1):]
                space = room - len(before) - len(word)
                if len(after) > space:
                    after = after[:max(space - 1, 0)] + "…"
                lines.append(lit("      ") + lead + faint(loc) + lit("  ") + fg(MUTED, before)
                             + bold_fg(tier_colour(tier), word) + fg(MUTED, after))
                if caret:
                    pad = 6 + lead_w + loc_w + 2 + len(before)
                    lines.append(lit(" " * pad) + fg(tier_colour(tier), "^"))
        lines.append("")
    return lines + footer(d, width, jev)


# ---------------------------------------------------------------------------------------
# 8. Tell first with a caret: design 5, with one ^ under the start of the caught word.


def tell_first_caret(d, files, width, jev):
    return tell_first(d, files, width, jev, caret=True)


DESIGNS = {"1": ledger, "2": snippet, "5": tell_first, "8": tell_first_caret}


def clean(d, width):
    return ["", lit("  ") + pill(ACCENT, "deslopper") + lit(" ") + bold("lint"), "",
            lit("  ") + fg(OK, "✔ ") + bold_fg(OK, "no slop found"), ""]


def main(argv):
    jev = "--jev" in argv
    width = int(os.environ.get("COLUMNS") or subprocess.run(
        ["tput", "cols"], capture_output=True, text=True).stdout.strip() or 100)
    width = min(width, 110)
    if "--width" in argv:
        width = int(argv[argv.index("--width") + 1])
    source = argv[argv.index("--from") + 1] if "--from" in argv else None
    which = next((a for a in argv if a in DESIGNS), "1")
    d, files, jev = load(jev, source)
    if not d["findings"]:
        render(clean(d, width))
        return
    lines = DESIGNS[which](d, files, width, jev)
    if lines is not None:
        render(lines)


if __name__ == "__main__":
    main(sys.argv[1:])
