"""Compliance verification for policy enforcement."""
from __future__ import annotations

import logging
from typing import Iterable, List

from genesis.cluster.node import ClusterNodeService
from genesis.governance.policy import PolicyEngine, PolicyEvent, PolicyRule, ResourceUsage

LOGGER = logging.getLogger(__name__)


class ComplianceChecker:
    """Evaluates resource usage and records policy events."""

    def __init__(self, engine: PolicyEngine, cluster: ClusterNodeService) -> None:
        self.engine = engine
        self.cluster = cluster

    def evaluate(self, usage: ResourceUsage) -> List[PolicyEvent]:
        events = self.engine.evaluate(usage)
        for event in events:
            LOGGER.warning("Policy violation detected: %s", event)
            self.cluster.record_policy_violation()
        return events

    def load_rules(self, rules: Iterable[PolicyRule]) -> None:
        for rule in rules:
            self.engine.add_rule(rule)
