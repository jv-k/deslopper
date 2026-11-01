"""The line scanner. A faithful port of the verified deslop-lint core.

`scan_prose` owns the block structure: it decides which lines are prose (not front
matter, not fenced or inline code, not MDX ESM, not inside an exempt region) and masks
what a tell must not see. In an Astro file the first-line `---` fence is code, and
`FenceLexer` masks all of it except the text inside its string literals. `lint_file` is
then a thin runner over the prose lines.
"""

import re
from dataclasses import dataclass
from enum import Enum, auto

from .smells import Smell, LintResult

FRONT_OPEN = re.compile(r"^---\s*$")
FRONT_CLOSE = re.compile(r"^(---|\.\.\.)\s*$")
# Astro's code fence closes only on a bare `---`, never on the YAML `...` closer.
ASTRO_FENCE_CLOSE = FRONT_OPEN
# A fence is indented at most 3 spaces (4+ is indented code, not a fence); the rest of
# the line is the info string. `scan_prose` applies the CommonMark opener/closer rules.
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
# A code span opens on a maximal backtick run and closes on a run of the exact same
# length. The lookarounds keep the closer maximal, so a 2-backtick opener is not closed
# by two of a longer run, which would mask the prose between as code.
INLINE_CODE = re.compile(r"(?<!`)(`+).*?(?<!`)\1(?!`)")
ENTITY = re.compile(r"&#?[0-9a-zA-Z]+;")
# The directive is exactly `-disable-line`, `-disable`, or `-enable`; the lookaheads stop
# an unknown suffix (`-disable-next-line`, `-disable-line-foo`) from matching any of them.
DISABLE_LINE = re.compile(r"<!--\s*deslop-lint-disable-line(?![-\w])[^>]*-->")
DISABLE = re.compile(r"<!--\s*deslop-lint-disable(?![-\w])[^>]*-->")
ENABLE = re.compile(r"<!--\s*deslop-lint-enable(?![-\w])[^>]*-->")
# In .mdx, a top-level line that starts with import/export is an ESM statement,
# not prose. Skip those lines so their punctuation is not scanned. JSX is left
# alone: it wraps rendered prose that should still be linted.
MDX_ESM = re.compile(r"^(import|export)\b")
# In the Astro fence an import statement is skipped, so its module specifier is never read
# as copy. `import.meta` and `import(` start expressions, so those lines are lexed. An
# export line is lexed like any other, because `export const` often holds copy.
ASTRO_IMPORT = re.compile(r"^import\b(?![.(])")


class Dialect(Enum):
    """The file type the scanner reads. The scanner's file-type rules live here.

    The dialect decides how the first-line `---` block is read and whether top-level
    import/export lines are ESM. Markdown and MDX skip the block as front matter. Astro
    reads it as a code fence whose string literals are prose.
    """
    MARKDOWN = auto()
    MDX = auto()
    ASTRO = auto()

    @property
    def first_block_close(self) -> "re.Pattern":
        """The line that closes a first-line `---` block: front matter or an Astro fence."""
        return ASTRO_FENCE_CLOSE if self is Dialect.ASTRO else FRONT_CLOSE

    @property
    def lexes_first_block(self) -> bool:
        """Whether the first-line `---` block is an Astro fence to lex, not front matter."""
        return self is Dialect.ASTRO

    @property
    def skips_esm(self) -> bool:
        return self is Dialect.MDX


_DIALECT_BY_EXTENSION = {".mdx": Dialect.MDX, ".astro": Dialect.ASTRO}


def dialect_for(path: str) -> Dialect:
    """The dialect for a path, by its extension. Anything unlisted is Markdown."""
    for ext, dialect in _DIALECT_BY_EXTENSION.items():
        if path.endswith(ext):
            return dialect
    return Dialect.MARKDOWN


def _blank(match: "re.Match") -> str:
    return " " * len(match.group(0))


class FenceTracker:
    """The fenced-code state machine, shared by the scanner and the digest.

    Feed lines in order; each is classified as 'open', 'inside', 'close', or
    'prose'. An invalid opener (a backtick fence with a backtick in its info
    string) classifies as prose, per CommonMark.
    """

    def __init__(self):
        self.active = False
        self._marker = ""
        self._length = 0

    def feed(self, line: str) -> str:
        fence = FENCE.match(line)
        if self.active:
            if fence:
                run, rest = fence.group(1), fence.group(2)
                # Only a bare run of the same char, at least as long, closes the block.
                if run[0] == self._marker and len(run) >= self._length and not rest.strip():
                    self.active = False
                    return "close"
            return "inside"
        if fence:
            run, rest = fence.group(1), fence.group(2)
            if run[0] != "`" or "`" not in rest:
                self.active, self._marker, self._length = True, run[0], len(run)
                return "open"
        return "prose"


class FenceLexer:
    """Masks the code in Astro fence lines and keeps the text of their string literals.

    Feed the fence lines in order. Each comes back the same length, with everything
    outside a literal blanked to spaces, the quote characters included, so a match offset
    is still the source column. A backslash escapes the next character inside a literal;
    escapes are not decoded. A single- or double-quoted literal that reaches the end of
    the line without a closer ends there and does not carry to the next line.

    A backtick opens a template literal, which runs to its closing backtick across lines
    if need be. Inside it, `${` opens an interpolation that is code up to its matching
    `}`. The lexer counts the braces in the interpolation, and a literal nested in it is
    masked with it.

    A `//` line comment runs to the end of its line and a `/* */` block comment to its
    closer, across lines if need be. Both are masked whole, so a quote inside one opens no
    literal. `feed` also returns the text of each comment on the line, delimiters
    stripped, so the scanner can read directives from it.

    The state carried across lines is an open block comment and the nesting of open
    template literals, interpolations, and the braces inside interpolations.
    """

    QUOTES = "'\""
    TEMPLATE, INTERPOLATION, BRACE = "`", "${", "{"

    def __init__(self):
        # True while a block comment is open at the end of the last line fed.
        self.in_block_comment = False
        # Open template literals, interpolations and braces inside them, innermost last.
        self._nesting = []

    @property
    def at_top_level(self) -> bool:
        """Whether the next line starts in plain code, not in a comment or a template."""
        return not self.in_block_comment and not self._nesting

    def feed(self, line: str) -> tuple[str, list[str]]:
        """Return the masked line and the text of each comment on it, in order."""
        out = []
        comments = []
        quote = None
        i = 0
        if self.in_block_comment:
            i = self._consume_block_comment(line, 0, comments)
            out.append(" " * i)
        while i < len(line):
            ch = line[i]
            in_template = quote is None and self._nesting[-1:] == [self.TEMPLATE]
            if quote is not None or in_template:
                # A quoted literal shows only in plain code, and template text only
                # outside every interpolation. A literal nested in code is masked.
                if quote is not None:
                    shown = not self._nesting
                else:
                    shown = self.INTERPOLATION not in self._nesting
                if ch == "\\" and i + 1 < len(line):
                    out.append(line[i:i + 2] if shown else "  ")
                    i += 2
                    continue
                if in_template and line.startswith("${", i):
                    self._nesting.append(self.INTERPOLATION)
                    out.append("  ")
                    i += 2
                    continue
                if ch == (quote or self.TEMPLATE):
                    if in_template:
                        self._nesting.pop()
                    quote = None
                    out.append(" ")
                else:
                    out.append(ch if shown else " ")
                i += 1
                continue
            if line.startswith("//", i):
                comments.append(line[i + 2:])
                out.append(" " * (len(line) - i))
                break
            if line.startswith("/*", i):
                end = self._consume_block_comment(line, i + 2, comments)
                out.append(" " * (end - i))
                i = end
                continue
            if ch in self.QUOTES:
                quote = ch
            elif ch == self.TEMPLATE:
                self._nesting.append(self.TEMPLATE)
            elif ch == "{" and self._nesting:
                self._nesting.append(self.BRACE)
            elif ch == "}" and self._nesting:
                self._nesting.pop()
            out.append(" ")
            i += 1
        return "".join(out), comments

    def _consume_block_comment(self, line: str, start: int, comments: list[str]) -> int:
        """Read block comment text from `start` and return the index just after it.

        The text is appended to `comments`. The comment stays open past the line end when
        `*/` is not on the line.
        """
        close = line.find("*/", start)
        self.in_block_comment = close < 0
        end = len(line) if close < 0 else close
        comments.append(line[start:end])
        return end if close < 0 else close + 2


@dataclass(frozen=True)
class ProseLine:
    """One prose line a tell sees: its 1-based number and the masked text for each phase.

    `pre_entity` has inline code blanked; `post_entity` has HTML entities blanked too.
    Both keep the original length, so a match offset is still the source column.
    """
    lineno: int
    pre_entity: str
    post_entity: str


def scan_prose(raw_lines, dialect=Dialect.MARKDOWN):
    """Yield a ProseLine for each line that is prose, in order.

    Skips front matter, fenced code, MDX ESM statements, and exempt regions, and masks
    inline code and HTML entities. The dialect says which of those rules apply. In an
    Astro fence each line is lexed instead: its string literals stay and the code around
    them is masked, then HTML entities are masked as for prose. Line endings on the input
    are tolerated, not required.
    """
    fences = FenceTracker()
    in_first_block = False
    lexer = None
    disabled = False
    first = True

    for ln, raw in enumerate(raw_lines, 1):
        line = raw[:-1] if raw.endswith("\n") else raw

        if first:
            first = False
            if FRONT_OPEN.match(line):
                in_first_block = True
                if dialect.lexes_first_block:
                    lexer = FenceLexer()
                continue
        if in_first_block:
            if dialect.first_block_close.match(line):
                in_first_block = False
                lexer = None
            elif lexer is not None:
                # An import line is lexed too, so a comment it opens still carries.
                is_import = lexer.at_top_level and ASTRO_IMPORT.match(line)
                masked, _comments = lexer.feed(line)
                if not is_import:
                    yield ProseLine(ln, masked, ENTITY.sub(_blank, masked))
            continue

        if fences.feed(line) != "prose":
            continue

        if dialect.skips_esm and MDX_ESM.match(line):
            continue

        masked = INLINE_CODE.sub(_blank, line)

        if DISABLE_LINE.search(masked):
            continue
        if DISABLE.search(masked):
            disabled = True
            continue
        if ENABLE.search(masked):
            disabled = False
            continue
        if disabled:
            continue

        yield ProseLine(ln, masked, ENTITY.sub(_blank, masked))


def _run_tells(tells, text, path, ln):
    for tell in tells:
        for off in tell.matcher(text):
            yield Smell(path, ln, off + 1, tell.tier, tell.name, tell.message)
            if tell.scope == "first":
                break


def lint_file(display_path, read_path, pre_tells, post_tells):
    try:
        with open(read_path, encoding="utf-8", newline="\n") as fh:
            raw_lines = fh.readlines()
    except OSError:
        return [], False

    smells = []
    for prose in scan_prose(raw_lines, dialect_for(display_path)):
        smells.extend(_run_tells(pre_tells, prose.pre_entity, display_path, prose.lineno))
        smells.extend(_run_tells(post_tells, prose.post_entity, display_path, prose.lineno))
    # Tells run one after another, so a line's smells arrive in tell order. Sort them
    # into reading order; the sort is stable, so a shared column keeps the tell order.
    smells.sort(key=lambda f: (f.line, f.col))
    return smells, True


def lint_files(items, tells) -> LintResult:
    pre = [t for t in tells if t.phase == "pre-entity"]
    post = [t for t in tells if t.phase != "pre-entity"]
    result = LintResult()
    for display_path, read_path in items:
        found, ok = lint_file(display_path, read_path, pre, post)
        if ok:
            result.smells.extend(found)
        else:
            result.unreadable.append(display_path)
    return result
