"""Simple token bucket rate limiter for orchestration."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Tuple

from genesis.metrics import genesis_rate_limit_drops_total


@dataclass(slots=True)
class RateLimitConfig:
    """Configuration for the token bucket."""

    rate_per_sec: float = 100.0
    burst: float = 50.0


class TokenBucketRateLimiter:
    """In-memory rate limiter keyed by task and optional identifier."""

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self._config = config or RateLimitConfig()
        self._state: Dict[str, Tuple[float, float]] = {}

    def allow(self, task_type: str, *, key: str | None = None) -> bool:
        bucket_key = self._make_key(task_type, key)
        now = time.monotonic()
        tokens, last_refill = self._state.get(bucket_key, (self._config.burst, now))
        elapsed = max(0.0, now - last_refill)
        tokens = min(self._config.burst, tokens + elapsed * self._config.rate_per_sec)
        if tokens < 1.0:
            genesis_rate_limit_drops_total.labels(task_type).inc()
            self._state[bucket_key] = (tokens, now)
            return False
        tokens -= 1.0
        self._state[bucket_key] = (tokens, now)
        return True

    @staticmethod
    def _make_key(task_type: str, key: str | None) -> str:
        if key:
            return f"{task_type}:{key}"
        return task_type


__all__ = ["RateLimitConfig", "TokenBucketRateLimiter"]
