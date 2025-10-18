"""Experiment planning utilities."""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import List, Mapping, Sequence

from genesis.metrics import genesis_hypotheses_generated_total
from genesis.knowledge import KnowledgeGraph, KnowledgeNodeType, KnowledgeRetriever
from genesis.research import ExperimentPlan


@dataclass(slots=True)
class PlannerContext:
    """Inputs collected prior to planning."""

    goal: str
    performance_gaps: Mapping[str, float]
    prior_metrics: Mapping[str, Sequence[float]]


class ExperimentPlanner:
    """Generate experiment plans from knowledge graph context."""

    def __init__(self, graph: KnowledgeGraph, retriever: KnowledgeRetriever) -> None:
        self._graph = graph
        self._retriever = retriever

    def propose(self, context: PlannerContext, *, limit: int = 1) -> List[ExperimentPlan]:
        """Generate one or more experiment plans for *goal*."""

        plans: List[ExperimentPlan] = []
        candidate_metrics = self._select_metrics(context.performance_gaps)
        for metric, target in candidate_metrics.items():
            hypothesis = self._build_hypothesis(context.goal, metric, target)
            controls = {"metric": metric, "target": target}
            plan = ExperimentPlan(
                goal=context.goal,
                hypothesis=hypothesis,
                controls=controls,
                metrics={metric: target},
                seed=self._seed_for_metric(metric),
                metadata={"related_nodes": self._related_modules(metric)},
            )
            plans.append(plan)
            genesis_hypotheses_generated_total.inc()
            if len(plans) >= limit:
                break
        return plans

    def _select_metrics(self, gaps: Mapping[str, float]) -> Mapping[str, float]:
        if gaps:
            return dict(sorted(gaps.items(), key=lambda item: item[1], reverse=True))
        historical = {
            node.label: self._mean_performance(node.label)
            for node in self._graph.nodes_by_type(KnowledgeNodeType.METRIC)
        }
        if not historical:
            return {"reward": 1.0}
        return historical

    def _build_hypothesis(self, goal: str, metric: str, target: float) -> str:
        return f"Improving {metric} to {target:.3f} will advance {goal}"

    def _seed_for_metric(self, metric: str) -> int:
        return sum(ord(char) for char in metric) % 10_000

    def _mean_performance(self, metric: str) -> float:
        values: List[float] = []
        for node in self._graph.nodes_by_type(KnowledgeNodeType.EXPERIMENT):
            value = node.properties.get(metric)
            if isinstance(value, (int, float)):
                values.append(float(value))
        if values:
            return statistics.mean(values)
        return 0.0

    def _related_modules(self, metric: str) -> List[str]:
        vector = [float(ord(char)) for char in metric]
        retrieved = self._retriever.by_embedding(vector, limit=3)
        modules = [node.label for node in retrieved.nodes if node.type == KnowledgeNodeType.MODULE]
        return modules


__all__ = ["ExperimentPlanner", "PlannerContext"]
