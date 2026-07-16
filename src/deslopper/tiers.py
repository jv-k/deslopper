"""The tier taxonomy: the closed set of tell severities and how each one behaves.

A tier is `error` or `warn` and nothing else. This module owns what that means — the
github annotation level and whether a finding of that tier fails a lint — so the
formatter, the exit-code rule, and the compiler read one table instead of each
hardcoding the tier names.
"""

_GITHUB_LEVEL = {"error": "error", "warn": "warning"}
# Tiers that fail a lint only when strict is set; every other known tier fails on its own.
_STRICT_ONLY = frozenset({"warn"})

KNOWN = frozenset(_GITHUB_LEVEL)


def is_known(tier) -> bool:
    return tier in KNOWN


def github_level(tier: str) -> str:
    return _GITHUB_LEVEL[tier]


def is_failing(tier: str, strict: bool) -> bool:
    """Whether a finding of this tier fails the lint, given the strict flag."""
    return strict or tier not in _STRICT_ONLY
