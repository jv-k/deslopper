"""Rule kinds and tell compilation.

A kind is a factory `(spec: dict, flags: int) -> Matcher`, where a Matcher is
`(masked_line: str) -> Iterable[int]` yielding 0-based match offsets. The engine wraps
every kind uniformly with phase, scope, tier, name, and message.
"""

import re
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from .errors import ConfigError

Matcher = Callable[[str], Iterable[int]]

FLAG_CHARS = {"i": re.IGNORECASE}
BOLD_TERMINAL = re.compile(r"[.:?!]$")
NON_SPACE = re.compile(r"\S")
# What has to follow an id label for it to read as a tag on the item rather than the
# subject of the sentence: an optional separator, then item text that opens capitalised.
ID_LABEL_TAIL = re.compile(r"[:).]?\s+(?:[-\u2013\u2014]\s*)?[*_\"']?[A-Z]")


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


def _regex_matcher(spec: dict, flags: int) -> Matcher:
    rx = re.compile(spec["pattern"], flags)

    def match(text: str):
        for m in rx.finditer(text):
            yield m.start()

    return match


def _bold_bullet_matcher(spec: dict, flags: int) -> Matcher:
    rx = re.compile(spec["pattern"], flags)

    def match(text: str):
        m = rx.search(text)
        if m and not BOLD_TERMINAL.search(m.group(3)) and NON_SPACE.search(m.group(4)):
            yield len(m.group(1))

    return match


def _id_label_matcher(spec: dict, flags: int) -> Matcher:
    rx = re.compile(spec["pattern"], flags)

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
    spec = {**raw, "pattern": pattern}
    try:
        matcher = kinds[kind](spec, flags)
    except re.error as exc:
        raise ConfigError(f"tell {name!r} has an invalid pattern: {exc}") from exc
    phase = raw.get("phase", "post-entity")
    return CompiledTell(
        name=name,
        tier=raw["tier"],
        phase=phase,
        scope=raw.get("scope", "all"),
        message=raw["message"],
        matcher=matcher,
        key=(name, phase),
    )
