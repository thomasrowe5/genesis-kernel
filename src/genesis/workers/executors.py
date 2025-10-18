"""Worker task executors."""
from __future__ import annotations

import asyncio
import time
import urllib.request
from typing import Any, Callable, Dict


def fibonacci(n: int) -> int:
    if n < 0:
        raise ValueError("n must be non-negative")
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def http_fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as response:
        return response.read().decode()


def sleep(seconds: float) -> str:
    time.sleep(float(seconds))
    return "slept"


TASK_REGISTRY: Dict[str, Callable[..., Any]] = {
    "fibonacci": fibonacci,
    "http_fetch": http_fetch,
    "sleep": sleep,
}


async def execute_task(task_type: str, *args: Any, **kwargs: Any) -> Any:
    func = TASK_REGISTRY.get(task_type)
    if func is None:
        raise ValueError(f"Unknown task type {task_type}")
    return await asyncio.to_thread(func, *args, **kwargs)
