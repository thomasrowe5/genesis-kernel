"""Graceful shutdown helpers."""
from __future__ import annotations

import asyncio
import signal
from typing import Callable


def register_signal_handlers(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()

    def _handler() -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handler)


def run_with_graceful_shutdown(coro_factory: Callable[[asyncio.Event], "asyncio.Task[Any]"]):
    async def _runner() -> None:
        stop_event = asyncio.Event()
        register_signal_handlers(stop_event)
        task = asyncio.create_task(coro_factory(stop_event))
        await stop_event.wait()
        await task

    asyncio.run(_runner())
