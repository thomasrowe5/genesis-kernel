"""AutoTest Cloud client abstraction used by the evaluator service."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional

try:  # pragma: no cover - optional dependency
    import httpx
except Exception:  # pragma: no cover - httpx is optional for tests
    httpx = None  # type: ignore[assignment]


@dataclass(slots=True)
class AutoTestResult:
    """Structured representation of the AutoTest Cloud response."""

    metrics: Dict[str, float]
    passed: bool
    metadata: Dict[str, Any]


class AutoTestClient:
    """Thin asynchronous wrapper around the AutoTest Cloud HTTP API.

    The client deliberately keeps the surface small so that it can be mocked in
    unit tests. When no ``base_url`` is provided the client operates in a mock
    mode returning deterministic responses derived from the benchmark payload.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0) -> None:
        self._base_url = base_url
        self._timeout = timeout

    async def run_suite(self, module_name: str, payload: Dict[str, Any]) -> AutoTestResult:
        """Execute the AutoTest suite for ``module_name`` with ``payload``.

        Parameters
        ----------
        module_name:
            The logical name of the module under test.
        payload:
            The serialized benchmark configuration that should be forwarded to
            AutoTest Cloud.
        """

        if self._base_url and httpx is None:  # pragma: no cover - defensive
            raise RuntimeError("httpx is required for real AutoTest interactions")

        if not self._base_url:
            # Mock mode – echo back deterministic metrics so the optimizer can
            # run inside CI without remote dependencies.
            latency = float(payload.get("expected_latency", 0.1))
            accuracy = float(payload.get("expected_accuracy", 1.0))
            stability = float(payload.get("expected_stability", 1.0))
            metadata = {
                "benchmark": payload.get("name", module_name),
                "cases": len(payload.get("cases", [])),
                "mode": "mock",
            }
            await asyncio.sleep(0)  # allow scheduling in async tests
            return AutoTestResult(
                metrics={
                    "latency": latency,
                    "accuracy": accuracy,
                    "stability": stability,
                },
                passed=True,
                metadata=metadata,
            )

        assert httpx is not None  # nosec - validated above
        async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:  # pragma: no cover - network path
            response = await client.post("/run", json={"module": module_name, **payload})
            response.raise_for_status()
            data: Dict[str, Any] = response.json()
            return AutoTestResult(
                metrics=data.get("metrics", {}),
                passed=bool(data.get("passed", False)),
                metadata=data.get("metadata", {}),
            )


__all__ = ["AutoTestClient", "AutoTestResult"]
