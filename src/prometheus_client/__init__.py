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


class Histogram(_Metric):
    pass


class Gauge(_Metric):
    pass


class Counter(_Metric):
    pass


__all__ = ["Histogram", "Gauge", "Counter"]
