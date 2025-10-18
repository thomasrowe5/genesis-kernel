"""Prometheus metric definitions for the Genesis kernel."""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# Histogram tracking the duration of each evaluator execution.
genesis_eval_duration_seconds = Histogram(
    "genesis_eval_duration_seconds",
    "Time spent running module evaluations via the AutoTest service.",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Gauge capturing the latest score emitted for a module variant.
genesis_module_score = Gauge(
    "genesis_module_score",
    "Composite reward score per module variant.",
    labelnames=("module", "version"),
)

# Counter recording module replacement events triggered by the optimizer.
genesis_replacements_total = Counter(
    "genesis_replacements_total",
    "Number of times the optimizer promoted a new module implementation.",
)

__all__ = [
    "genesis_eval_duration_seconds",
    "genesis_module_score",
    "genesis_replacements_total",
]
