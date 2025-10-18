"""Meta-learning utilities for deriving rules from experiments."""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Iterable, Mapping

from genesis.metrics import genesis_theorist_updates_total

from genesis.research import ExperimentResult


@dataclass(slots=True)
class TheoryUpdate:
    """Summary of a discovered trend."""

    statement: str
    metrics: Mapping[str, float]


class Theorist:
    """Accumulate experiment results and surface simple correlations."""

    def derive(self, experiments: Iterable[ExperimentResult]) -> TheoryUpdate:
        metrics: dict[str, list[float]] = {}
        for experiment in experiments:
            for metric, value in experiment.metrics.items():
                metrics.setdefault(metric, []).append(value)
        summaries = {metric: statistics.mean(values) for metric, values in metrics.items() if values}
        if not summaries:
            statement = "No trends available"
        else:
            best_metric = max(summaries, key=summaries.get)
            statement = f"Performance trends upward with {best_metric}={summaries[best_metric]:.3f}"
        genesis_theorist_updates_total.inc()
        return TheoryUpdate(statement=statement, metrics=summaries)


__all__ = ["Theorist", "TheoryUpdate"]
