"""Policy definition and enforcement utilities."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional


@dataclass
class PolicyRule:
    id: str
    name: str
    type: str
    threshold: float
    active: bool = True


@dataclass
class ResourceUsage:
    cpu_percent: float
    memory_mb: float
    network_io_mb: float
    evals_running: int
    compute_seconds: float


@dataclass
class PolicyEvent:
    rule_id: str
    at: dt.datetime
    level: str
    data: Mapping[str, float]


class PolicyEngine:
    """Evaluates system metrics against policy thresholds."""

    def __init__(self, rules: Optional[Iterable[PolicyRule]] = None) -> None:
        self._rules: MutableMapping[str, PolicyRule] = {}
        if rules:
            for rule in rules:
                self._rules[rule.id] = rule

    def update_rules(self, rules: Iterable[PolicyRule]) -> None:
        self._rules = {rule.id: rule for rule in rules}

    def add_rule(self, rule: PolicyRule) -> None:
        self._rules[rule.id] = rule

    def rules(self) -> List[PolicyRule]:
        return list(self._rules.values())

    def evaluate(self, usage: ResourceUsage) -> List[PolicyEvent]:
        events: List[PolicyEvent] = []
        now = dt.datetime.now(tz=dt.timezone.utc)
        metrics = {
            "cpu": usage.cpu_percent,
            "memory": usage.memory_mb,
            "network": usage.network_io_mb,
            "evals": float(usage.evals_running),
            "compute_seconds": usage.compute_seconds,
        }
        for rule in self._rules.values():
            if not rule.active:
                continue
            current_value = metrics.get(rule.type)
            if current_value is None:
                continue
            if current_value > rule.threshold:
                events.append(
                    PolicyEvent(
                        rule_id=rule.id,
                        at=now,
                        level="violation",
                        data={"value": current_value, "threshold": rule.threshold},
                    )
                )
        return events

    def summary(self) -> Dict[str, float]:
        return {rule.id: rule.threshold for rule in self._rules.values()}
