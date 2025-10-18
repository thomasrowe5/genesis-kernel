"""Minimal Prometheus client stubs for offline testing."""
from __future__ import annotations

from typing import Any, Tuple


class _Metric:
    def __init__(self, name: str, documentation: str, labelnames: Tuple[str, ...] | None = None, **kwargs: Any) -> None:
        self.name = name
        self.documentation = documentation
        self.labelnames = labelnames or ()
        self.kwargs = kwargs
        self._last_value: float | None = None
        self._value = _MetricValue(self)

    def labels(self, *args: Any, **kwargs: Any) -> "_Metric":
        return self

    def observe(self, value: float) -> None:  # pragma: no cover - side effect free stub
        self._last_value = value

    def set(self, value: float) -> None:  # pragma: no cover - side effect free stub
        self._last_value = value

    def inc(self, amount: float = 1.0) -> None:  # pragma: no cover - side effect free stub
        if self._last_value is None:
            self._last_value = 0.0
        self._last_value += amount

    def time(self) -> "_MetricTimer":
        return _MetricTimer(self)


class _MetricValue:
    def __init__(self, metric: _Metric) -> None:
        self._metric = metric

    def get(self) -> float:
        return float(self._metric._last_value or 0.0)


class Histogram(_Metric):
    pass


class Gauge(_Metric):
    pass


class Counter(_Metric):
    pass


class _MetricTimer:
    def __init__(self, metric: _Metric) -> None:
        self._metric = metric

    def __enter__(self) -> "_MetricTimer":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._metric.observe(0.0)


__all__ = ["Histogram", "Gauge", "Counter"]
