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


BUILTIN_KINDS = {
    "regex": _regex_matcher,
    "bold-bullet": _bold_bullet_matcher,
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
