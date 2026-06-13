"""Finding and LintResult value types."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    col: int
    tier: str
    name: str
    message: str


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
