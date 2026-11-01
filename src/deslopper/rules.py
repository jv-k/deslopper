"""Rule kinds and tell compilation.

A kind is a factory `(spec: dict, flags: int) -> Matcher`, where a Matcher is
`(masked_line: str) -> Iterable[int]` yielding 0-based match offsets. The engine wraps
every kind uniformly with phase, scope, tier, name, and message.
"""

import re
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from . import tiers
from .errors import ConfigError

Matcher = Callable[[str], Iterable[int]]

FLAG_CHARS = {"i": re.IGNORECASE}
BOLD_TERMINAL = re.compile(r"[.:?!]$")
NON_SPACE = re.compile(r"\S")
# What has to follow an id label for it to read as a tag on the item rather than the
# subject of the sentence: an optional separator, then item text that opens capitalised.
ID_LABEL_TAIL = re.compile(r"[:).]?\s+(?:[-\u2013\u2014]\s*)?[*_\"']?[A-Z]")


CURLY_APOSTROPHE = "\u2019"
# What a bare apostrophe becomes.
EITHER_APOSTROPHE = "['" + CURLY_APOSTROPHE + "]"


def _widen_apostrophes(pattern: str) -> str:
    """Let each apostrophe in a pattern match the straight and the curly form.

    A bare or escaped ' becomes either apostrophe. A character class that holds one is
    left as written and wrapped instead: [a'] becomes (?:[a']|’) and [^'] becomes
    (?:(?!’)[^']), so a negated class keeps out both forms and no range inside the
    class changes. Only a ' written as itself counts: an escape such as \\x27 is left
    alone. Only the pattern changes: the input is never folded, so a tell for the curly
    character still sees it.
    """
    out = []
    i, n = 0, len(pattern)
    class_start = None  # index in out where the open class begins
    negated = has_apostrophe = False
    while i < n:
        ch = pattern[i]
        if ch == "\\" and i + 1 < n:
            esc = pattern[i:i + 2]
            if esc == "\\'" and class_start is None:
                out.append(EITHER_APOSTROPHE)
            else:
                has_apostrophe |= esc == "\\'"
                out.append(esc)
            i += 2
            continue
        if class_start is not None:
            has_apostrophe |= ch == "'"
            out.append(ch)
            if ch == "]":
                if has_apostrophe:
                    cls = "".join(out[class_start:])
                    del out[class_start:]
                    if negated:
                        out.append("(?:(?!" + CURLY_APOSTROPHE + ")" + cls + ")")
                    else:
                        out.append("(?:" + cls + "|" + CURLY_APOSTROPHE + ")")
                class_start = None
            i += 1
            continue
        if ch == "[":
            # A ] straight after the opening [ or [^ is a literal, not the close.
            j = i + 1
            negated = j < n and pattern[j] == "^"
            if negated:
                j += 1
            if j < n and pattern[j] == "]":
                j += 1
            class_start, has_apostrophe = len(out), False
            out.append(pattern[i:j])
            i = j
            continue
        out.append(EITHER_APOSTROPHE if ch == "'" else ch)
        i += 1
    return "".join(out)


@dataclass(frozen=True)
class CompiledTell:
    name: str
    tier: str
    phase: str
    scope: str
    message: str
    matcher: Matcher
    key: tuple


def _parse_flags(spec_flags: str) -> int:
    flags = 0
    for ch in spec_flags:
        if ch not in FLAG_CHARS:
            raise ConfigError(f"unknown flag character {ch!r}")
        flags |= FLAG_CHARS[ch]
    return flags


def _compile_with_groups(spec: dict, flags: int, n: int) -> "re.Pattern":
    """Compile a pattern for a kind that reads its capture groups by number."""
    rx = re.compile(spec["pattern"], flags)
    if rx.groups < n:
        raise ConfigError(
            f"tell {spec.get('name', '<unnamed>')!r} of kind {spec.get('kind')!r} needs "
            f"{n} capture groups, its pattern has {rx.groups}"
        )
    return rx


def _regex_matcher(spec: dict, flags: int) -> Matcher:
    rx = re.compile(spec["pattern"], flags)

    def match(text: str):
        for m in rx.finditer(text):
            yield m.start()

    return match


def _bold_bullet_matcher(spec: dict, flags: int) -> Matcher:
    rx = _compile_with_groups(spec, flags, 4)

    def match(text: str):
        m = rx.search(text)
        if m and not BOLD_TERMINAL.search(m.group(3)) and NON_SPACE.search(m.group(4)):
            yield len(m.group(1))

    return match


def _id_label_matcher(spec: dict, flags: int) -> Matcher:
    rx = _compile_with_groups(spec, flags, 4)

    def match(text: str):
        m = rx.search(text)
        if not m:
            return
        marker, bold, rest = m.group(1), m.group(2), m.group(4)
        if bold:
            # A bold run has to close on the label itself. '**S3 Node:**' names a thing;
            # '**G1**' tags an item.
            if not rest.startswith(bold):
                return
            rest = rest[len(bold):]
        if ID_LABEL_TAIL.match(rest):
            yield len(marker)

    return match


BUILTIN_KINDS = {
    "regex": _regex_matcher,
    "bold-bullet": _bold_bullet_matcher,
    "id-label": _id_label_matcher,
}


def compile_tell(raw: dict, extra_kinds: Optional[dict] = None) -> CompiledTell:
    kinds = dict(BUILTIN_KINDS)
    if extra_kinds:
        kinds.update(extra_kinds)
    name = raw.get("name", "<unnamed>")
    tier = raw.get("tier")
    if not tiers.is_known(tier):
        raise ConfigError(
            f"tell {name!r} has tier {tier!r}; tiers are {', '.join(sorted(tiers.KNOWN))}"
        )
    kind = raw.get("kind", "regex")
    if kind not in kinds:
        raise ConfigError(f"tell {name!r} uses unknown kind {kind!r}")
    flags = _parse_flags(raw.get("flags", ""))
    if "words" in raw:
        pattern = r"\b(?:" + "|".join(raw["words"]) + r")\b"
    elif "pattern" in raw:
        pattern = raw["pattern"]
    else:
        raise ConfigError(f"tell {name!r} has neither pattern nor words")
    spec = {**raw, "pattern": _widen_apostrophes(pattern)}
    try:
        matcher = kinds[kind](spec, flags)
    except re.error as exc:
        # Report the error against the pattern as written, not the widened one, so its
        # position points at the user's text.
        try:
            re.compile(pattern, flags)
        except re.error as written:
            exc = written
        raise ConfigError(f"tell {name!r} has an invalid pattern: {exc}") from exc
    phase = raw.get("phase", "post-entity")
    return CompiledTell(
        name=name,
        tier=tier,
        phase=phase,
        scope=raw.get("scope", "all"),
        message=raw["message"],
        matcher=matcher,
        key=(name, phase),
    )
