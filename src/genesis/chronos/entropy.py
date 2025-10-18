"""Entropy utilities supporting temporal recursion safety checks."""
from __future__ import annotations

import math
from typing import Mapping


def _probabilities(metrics: Mapping[str, float]) -> list[float]:
    positive = [max(value, 0.0) for value in metrics.values() if value != 0]
    if not positive:
        return []
    total = sum(positive)
    if total == 0:
        return []
    return [value / total for value in positive]


def shannon_entropy(metrics: Mapping[str, float]) -> float:
    """Compute Shannon entropy for a metric distribution."""

    probabilities = _probabilities(metrics)
    if not probabilities:
        return 0.0
    return -sum(p * math.log2(p) for p in probabilities if p > 0)


def compute_entropy_delta(predicted: Mapping[str, float], actual: Mapping[str, float]) -> float:
    """Return the absolute entropy delta between predicted and actual metrics."""

    predicted_entropy = shannon_entropy(predicted)
    actual_entropy = shannon_entropy(actual)
    return abs(predicted_entropy - actual_entropy)


__all__ = ["compute_entropy_delta", "shannon_entropy"]
