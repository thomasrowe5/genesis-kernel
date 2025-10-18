"""Continuity evaluation for temporal branch management."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Mapping, Sequence


@dataclass(slots=True)
class ContinuityStatus:
    """Represents the continuity evaluation of a branch merge."""

    score: float
    violations: List[str] = field(default_factory=list)
    delta: float = 0.0

    @property
    def is_consistent(self) -> bool:
        return not self.violations and self.score >= 1.0


class ContinuityEnforcer:
    """Enforces temporal continuity constraints using a simple rule-set."""

    def __init__(self, ethic_principles: Sequence[str] | None = None) -> None:
        self._principles = list(ethic_principles or [])

    @property
    def principles(self) -> Sequence[str]:
        return tuple(self._principles)

    def _ethical_violations(self, candidate: Mapping[str, object]) -> List[str]:
        violations: List[str] = []
        ethics_flag = candidate.get("ethical", True)
        if isinstance(ethics_flag, bool) and not ethics_flag:
            violations.append("ethic-breach")
        declared = candidate.get("violations")
        if isinstance(declared, Iterable) and not isinstance(declared, (str, bytes)):
            violations.extend(str(item) for item in declared)
        return violations

    def evaluate(self, baseline: Mapping[str, float], candidate: Mapping[str, float]) -> ContinuityStatus:
        drift = sum(abs(candidate.get(key, 0.0) - baseline.get(key, 0.0)) for key in baseline)
        violations = self._ethical_violations(candidate)
        if violations and self._principles:
            violations.extend(self._principles)
        score = 1.0 if drift == 0.0 and not violations else max(0.0, 1.0 - min(drift, 1.0))
        return ContinuityStatus(score=score, violations=violations, delta=drift)


__all__ = ["ContinuityEnforcer", "ContinuityStatus"]
