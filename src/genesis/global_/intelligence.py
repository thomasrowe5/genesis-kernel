"""Aggregates global intelligence metrics across federations."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Deque, Dict, Mapping, MutableMapping, Optional

from genesis.metrics import (
    genesis_global_energy_mwh,
    genesis_latency_mean_ms,
    genesis_peace_index,
)


@dataclass(slots=True)
class GlobalMetricSample:
    key: str
    value: float
    unit: str
    at: datetime


class GlobalIntelligence:
    """Maintains rolling global metrics and composite indicators."""

    def __init__(self, window: int = 20) -> None:
        self._metrics: MutableMapping[str, Deque[GlobalMetricSample]] = {}
        self._window = window

    def record(self, key: str, value: float, unit: str, *, at: Optional[datetime] = None) -> None:
        sample = GlobalMetricSample(key=key, value=value, unit=unit, at=at or datetime.utcnow())
        queue = self._metrics.setdefault(key, deque(maxlen=self._window))
        queue.append(sample)
        self._refresh_prometheus(key)

    def _refresh_prometheus(self, key: str) -> None:
        if key == "energy_mwh":
            genesis_global_energy_mwh.set(self.average(key))
        elif key == "latency_ms":
            genesis_latency_mean_ms.set(self.average(key))
        elif key == "peace_index":
            genesis_peace_index.set(self.average(key))

    def average(self, key: str) -> float:
        samples = self._metrics.get(key)
        if not samples:
            return 0.0
        return mean(sample.value for sample in samples)

    def snapshot(self) -> Mapping[str, Mapping[str, float]]:
        data: Dict[str, Mapping[str, float]] = {}
        for key, samples in self._metrics.items():
            data[key] = {
                "average": mean(sample.value for sample in samples),
                "latest": samples[-1].value,
                "count": float(len(samples)),
            }
        return data

    def trend(self, key: str) -> float:
        samples = self._metrics.get(key)
        if not samples or len(samples) < 2:
            return 0.0
        # Simple first-order difference normalised by window length.
        return (samples[-1].value - samples[0].value) / max(1, len(samples) - 1)

    def update_peace_index(self, treaties_active: int, disputes: int) -> float:
        total = treaties_active + disputes if treaties_active + disputes else 1
        peace_index = max(0.0, min(100.0, 100.0 * treaties_active / total))
        self.record("peace_index", peace_index, unit="index")
        return peace_index


__all__ = ["GlobalIntelligence", "GlobalMetricSample"]
