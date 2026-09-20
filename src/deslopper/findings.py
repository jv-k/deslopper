"""Finding and LintResult value types."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    col: int
    tier: str
    name: str
    message: str
    # A verdict is set by a judging pass, not by the engine, so both default to none
    # and every format renders a finding without one exactly as before.
    verdict: Optional[str] = None
    probability: Optional[float] = None


@dataclass
class LintResult:
    findings: list = field(default_factory=list)
    unreadable: list = field(default_factory=list)

    @property
    def errors(self) -> int:
        return sum(1 for f in self.findings if f.tier == "error")

    @property
    def warnings(self) -> int:
        return sum(1 for f in self.findings if f.tier == "warn")
