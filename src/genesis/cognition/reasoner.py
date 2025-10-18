"""Hybrid symbolic reasoning utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from genesis.metrics import genesis_reasoner_latency_seconds


@dataclass(slots=True)
class ReasoningRequest:
    """Comparison query for the reasoner."""

    module_a: str
    module_b: str
    metric: str
    observations: Mapping[str, Mapping[str, float]]


@dataclass(slots=True)
class ReasoningResponse:
    """Result produced by the reasoner."""

    statement: str
    confidence: float


class Reasoner:
    """Very small rule engine for module comparisons."""

    def evaluate(self, request: ReasoningRequest) -> ReasoningResponse:
        """Infer a simple causal statement from the observations."""

        with genesis_reasoner_latency_seconds.time():
            metric_values = request.observations.get(request.metric, {})
            value_a = metric_values.get(request.module_a)
            value_b = metric_values.get(request.module_b)
            if value_a is None or value_b is None:
                return ReasoningResponse(
                    statement=f"Insufficient data to compare {request.module_a} and {request.module_b}",
                    confidence=0.0,
                )
            if value_a > value_b:
                statement = (
                    f"{request.module_a} outperforms {request.module_b} on {request.metric} by "
                    f"{value_a - value_b:.3f}"
                )
            elif value_a < value_b:
                statement = (
                    f"{request.module_b} outperforms {request.module_a} on {request.metric} by "
                    f"{value_b - value_a:.3f}"
                )
            else:
                statement = f"{request.module_a} and {request.module_b} tie on {request.metric}"
            confidence = self._confidence(value_a, value_b)
            return ReasoningResponse(statement=statement, confidence=confidence)

    @staticmethod
    def _confidence(value_a: float, value_b: float) -> float:
        delta = abs(value_a - value_b)
        if delta == 0:
            return 0.1
        return min(0.99, 0.5 + delta / max(value_a, value_b, 1e-9))


__all__ = ["Reasoner", "ReasoningRequest", "ReasoningResponse"]
