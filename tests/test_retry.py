from __future__ import annotations

import asyncio

import pytest

from genesis.utils.retry import CircuitBreakerOpenError, RetryPolicy, retry, retry_async


def test_retry_succeeds_after_failures() -> None:
    attempts = {"count": 0}

    @retry(RetryPolicy(attempts=3, backoff_factor=0.0, jitter=0.0), operation="unit_test")
    def flaky() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ValueError("transient")
        return "ok"

    assert flaky() == "ok"
    assert attempts["count"] == 3


def test_retry_async_circuit_breaker_opens() -> None:
    policy = RetryPolicy(attempts=1, circuit_threshold=1, circuit_reset_seconds=1.0)

    @retry_async(policy, operation="async_test")
    async def always_fail() -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        asyncio.run(always_fail())
    with pytest.raises(CircuitBreakerOpenError):
        asyncio.run(always_fail())
