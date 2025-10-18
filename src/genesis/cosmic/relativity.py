"""Relativistic helpers for reasoning about asynchronous cosmic events."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence


C = 299_792_458  # speed of light in m/s, informational constant


def time_dilation_factor(velocity_fraction: float) -> float:
    """Return the Lorentz gamma factor for a velocity expressed as c fraction."""

    if not 0.0 <= velocity_fraction < 1.0:
        raise ValueError("velocity_fraction must be within [0, 1)")
    gamma = 1.0 / math.sqrt(1.0 - velocity_fraction**2)
    return gamma


def to_proper_time(timestamp: datetime, reference: datetime, velocity_fraction: float) -> float:
    """Convert a timestamp to proper seconds elapsed relative to a moving frame."""

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    delta = (timestamp - reference).total_seconds()
    gamma = time_dilation_factor(velocity_fraction)
    return delta / gamma


@dataclass(slots=True)
class CausalEvent:
    identifier: str
    timestamp: datetime
    velocity_fraction: float


def causal_order(events: Sequence[CausalEvent]) -> list[str]:
    """Sort event identifiers by causal order accounting for time dilation."""

    if not events:
        return []
    reference = min(events, key=lambda evt: evt.timestamp).timestamp
    normalized = [
        (
            evt.identifier,
            to_proper_time(evt.timestamp, reference, evt.velocity_fraction),
            evt.timestamp,
        )
        for evt in events
    ]
    normalized.sort(key=lambda item: (item[1], item[2]))
    return [identifier for identifier, _, _ in normalized]


__all__ = ["CausalEvent", "causal_order", "time_dilation_factor", "to_proper_time"]
