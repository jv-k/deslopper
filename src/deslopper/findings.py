"""Finding and LintResult value types."""

from dataclasses import dataclass, field
from typing import Optional

VERDICTS = ("keep", "rewrite")


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

    def __post_init__(self):
        # The pair is one unit and output.schema.json is its contract, so a finding
        # that could not render as valid JSON is refused here rather than by a format.
        if (self.verdict is None) != (self.probability is None):
            raise ValueError("verdict and probability are set together or not at all")
        if self.verdict is None:
            return
        if self.verdict not in VERDICTS:
            raise ValueError(f"verdict must be one of {VERDICTS}, not {self.verdict!r}")
        if not 0 <= self.probability <= 1:
            raise ValueError(f"probability must be within 0..1, not {self.probability!r}")


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

    @property
    def keep(self) -> int:
        return sum(1 for f in self.findings if f.verdict == "keep")

    @property
    def rewrite(self) -> int:
        return sum(1 for f in self.findings if f.verdict == "rewrite")
