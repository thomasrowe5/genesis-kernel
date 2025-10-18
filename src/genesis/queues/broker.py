"""Queue broker abstraction."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from redis.asyncio import Redis

from ..config import get_settings
from ..metrics import jobs_enqueued, queue_depth
from .schemas import JobPayload


@dataclass
class QueueMessage:
    job_id: int
    payload: JobPayload
    priority: int


class BaseBroker:
    async def enqueue(
        self,
        job_id: int,
        payload: JobPayload,
        priority: int = 0,
        dedupe_key: Optional[str] = None,
        dedupe_ttl: int = 0,
    ) -> bool:
        raise NotImplementedError

    async def dequeue(self, timeout: int = 1) -> Optional[QueueMessage]:
        raise NotImplementedError

    async def ack(self, job_id: int) -> None:  # pragma: no cover - interface only
        return None

    async def requeue(self, message: QueueMessage, delay: float) -> None:
        raise NotImplementedError

    async def depth(self) -> int:
        raise NotImplementedError


class RedisBroker(BaseBroker):
    """Redis backed broker using lists per priority."""

    def __init__(self, redis: Redis, *, max_priority: int = 3) -> None:
        self.redis = redis
        self.max_priority = max_priority
        self.queue_prefix = "genesis:queue"
        self.dedupe_prefix = "genesis:dedupe"

    def _queue_keys(self) -> Tuple[str, ...]:
        return tuple(f"{self.queue_prefix}:{priority}" for priority in range(self.max_priority + 1))

    async def enqueue(
        self,
        job_id: int,
        payload: JobPayload,
        priority: int = 0,
        dedupe_key: Optional[str] = None,
        dedupe_ttl: int = 0,
    ) -> bool:
        priority = max(0, min(priority, self.max_priority))
        if dedupe_key:
            key = f"{self.dedupe_prefix}:{dedupe_key}"
            if await self.redis.exists(key):
                return False
            await self.redis.set(key, job_id, ex=dedupe_ttl or get_settings().dedupe_ttl)
        queue_key = f"{self.queue_prefix}:{priority}"
        message = json.dumps({"job_id": job_id, "payload": payload.model_dump()})
        await self.redis.lpush(queue_key, message)
        jobs_enqueued.inc()
        await self._update_depth()
        return True

    async def dequeue(self, timeout: int = 1) -> Optional[QueueMessage]:
        keys = list(self._queue_keys())
        result = await self.redis.brpop(keys, timeout=timeout)
        if result is None:
            return None
        _queue, raw = result
        payload_raw = raw.decode() if isinstance(raw, bytes) else raw
        data = json.loads(payload_raw)
        payload = JobPayload(**data["payload"])
        priority = int(_queue.decode().split(":")[-1]) if isinstance(_queue, bytes) else int(_queue.split(":")[-1])
        await self._update_depth()
        return QueueMessage(job_id=int(data["job_id"]), payload=payload, priority=priority)

    async def ack(self, job_id: int) -> None:  # pragma: no cover - Redis ack is implicit
        await self._update_depth()

    async def requeue(self, message: QueueMessage, delay: float) -> None:
        await asyncio.sleep(delay)
        await self.enqueue(
            message.job_id,
            message.payload,
            priority=message.priority,
        )

    async def depth(self) -> int:
        lengths = await asyncio.gather(
            *(self.redis.llen(key) for key in self._queue_keys())
        )
        return int(sum(lengths))

    async def _update_depth(self) -> None:
        depth = await self.depth()
        queue_depth.set(depth)


class InMemoryBroker(BaseBroker):
    """In-memory broker used for tests."""

    def __init__(self) -> None:
        self.queues: Dict[int, asyncio.Queue[QueueMessage]] = {}

    def _queue(self, priority: int) -> asyncio.Queue[QueueMessage]:
        priority = max(priority, 0)
        if priority not in self.queues:
            self.queues[priority] = asyncio.Queue()
        return self.queues[priority]

    async def enqueue(
        self,
        job_id: int,
        payload: JobPayload,
        priority: int = 0,
        dedupe_key: Optional[str] = None,
        dedupe_ttl: int = 0,
    ) -> bool:
        await self._queue(priority).put(QueueMessage(job_id=job_id, payload=payload, priority=priority))
        jobs_enqueued.inc()
        await self._update_depth()
        return True

    async def dequeue(self, timeout: int = 1) -> Optional[QueueMessage]:
        if not self.queues:
            await asyncio.sleep(timeout)
            return None
        for priority in sorted(self.queues.keys(), reverse=True):
            queue = self.queues[priority]
            try:
                message = queue.get_nowait()
                await self._update_depth()
                return message
            except asyncio.QueueEmpty:
                continue
        await asyncio.sleep(timeout)
        return None

    async def requeue(self, message: QueueMessage, delay: float) -> None:
        await asyncio.sleep(delay)
        await self.enqueue(message.job_id, message.payload, priority=message.priority)

    async def depth(self) -> int:
        return int(sum(queue.qsize() for queue in self.queues.values()))

    async def _update_depth(self) -> None:
        queue_depth.set(await self.depth())
