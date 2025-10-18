"""Formal ethics principles enforced by the Genesis auditor."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass(slots=True)
class EthicsPrinciple:
    """Named ethical rule along with threshold metadata."""

    name: str
    description: str
    severity_threshold: float


DEFAULT_PRINCIPLES: List[EthicsPrinciple] = [
    EthicsPrinciple(
        name="safety",
        description="Prevent actions that could harm humans, infrastructure, or the federation itself.",
        severity_threshold=0.7,
    ),
    EthicsPrinciple(
        name="fairness",
        description="Ensure equitable access to resources and avoid biased behaviour.",
        severity_threshold=0.5,
    ),
    EthicsPrinciple(
        name="transparency",
        description="Maintain audit trails and explainability for automated decisions.",
        severity_threshold=0.4,
    ),
]


def active_principles() -> Iterable[EthicsPrinciple]:
    """Iterator over the current default principles."""

    return list(DEFAULT_PRINCIPLES)


__all__ = ["EthicsPrinciple", "DEFAULT_PRINCIPLES", "active_principles"]
