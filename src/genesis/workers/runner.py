"""Worker runner."""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

from redis.asyncio import Redis
from sqlmodel import select

from ..config import get_settings
from ..db import get_session, init_db
from ..logging import configure_logging
from ..metrics import job_duration, jobs_completed
from ..models import Event, Job, JobState, WorkerHeartbeat
from ..queues.broker import BaseBroker, InMemoryBroker, QueueMessage, RedisBroker
from .executors import execute_task
from .heartbeat import record_heartbeat

logger = logging.getLogger(__name__)


@dataclass
class WorkerContext:
    worker_id: str
    broker: BaseBroker
    stop_event: asyncio.Event


class WorkerRunner:
    def __init__(self, context: WorkerContext) -> None:
        self.context = context
        self.settings = get_settings()

    async def run(self) -> None:
        heartbeat_task = asyncio.create_task(
            record_heartbeat(
                self.context.worker_id,
                self.settings.worker_heartbeat_interval,
                self.context.stop_event,
            )
        )
        try:
            while not self.context.stop_event.is_set():
                message = await self.context.broker.dequeue(timeout=int(self.settings.worker_poll_interval))
                if message is None:
                    continue
                await self._process_message(message)
        finally:
            heartbeat_task.cancel()
            with contextlib.suppress(Exception):
                await heartbeat_task

    async def _process_message(self, message: QueueMessage) -> None:
        start = time.perf_counter()
        job = await asyncio.to_thread(self._mark_running, message.job_id)
        if job is None:
            logger.warning("Job not found", extra={"job_id": message.job_id})
            return
        try:
            result = await execute_task(job.task_type, *message.payload.args, **message.payload.kwargs)
        except Exception as exc:  # noqa: BLE001
            await asyncio.to_thread(self._mark_failed, job.id, str(exc), job.attempts)
            if job.attempts < self.settings.max_retries:
                delay = min(60.0, 2 ** job.attempts)
                await self.context.broker.requeue(message, delay)
            return
        duration = time.perf_counter() - start
        job_duration.observe(duration)
        await asyncio.to_thread(self._mark_succeeded, job.id, result)
        jobs_completed.labels(status=JobState.SUCCEEDED.value).inc()

    def _mark_running(self, job_id: int) -> Optional[Job]:
        with get_session() as session:
            job = session.get(Job, job_id)
            if job is None:
                return None
            job.state = JobState.RUNNING
            job.attempts += 1
            job.started_at = job.started_at or time_to_datetime()
            job.updated_at = time_to_datetime()
            session.add(job)
            session.add(Event(job_id=job_id, type="running"))
            self._update_in_flight(session, 1)
            session.commit()
            session.refresh(job)
            return job

    def _mark_succeeded(self, job_id: int, result: object) -> None:
        with get_session() as session:
            job = session.get(Job, job_id)
            if job is None:
                return
            job.state = JobState.SUCCEEDED
            job.finished_at = time_to_datetime()
            job.updated_at = time_to_datetime()
            job.result_json = json.dumps(result)
            session.add(job)
            session.add(Event(job_id=job_id, type="succeeded", data_json=job.result_json))
            self._update_in_flight(session, -1)
            self._increment_processed(session)
            session.commit()

    def _mark_failed(self, job_id: int, error: str, attempts: int) -> None:
        with get_session() as session:
            job = session.get(Job, job_id)
            if job is None:
                return
            job.state = JobState.FAILED if attempts < self.settings.max_retries else JobState.DEAD_LETTER
            job.finished_at = time_to_datetime()
            job.updated_at = time_to_datetime()
            job.error_text = error
            session.add(job)
            session.add(Event(job_id=job_id, type="failed", data_json=json.dumps({"error": error})))
            self._update_in_flight(session, -1)
            if job.state == JobState.DEAD_LETTER:
                self._increment_processed(session)
            session.commit()
            jobs_completed.labels(status=job.state.value).inc()

    def _update_in_flight(self, session, delta: int) -> None:
        heartbeat = session.exec(
            select(WorkerHeartbeat).where(WorkerHeartbeat.worker_id == self.context.worker_id)
        ).first()
        if heartbeat is None:
            heartbeat = WorkerHeartbeat(worker_id=self.context.worker_id, in_flight=max(delta, 0))
            session.add(heartbeat)
        else:
            heartbeat.in_flight = max(0, heartbeat.in_flight + delta)
            session.add(heartbeat)

    def _increment_processed(self, session) -> None:
        heartbeat = session.exec(
            select(WorkerHeartbeat).where(WorkerHeartbeat.worker_id == self.context.worker_id)
        ).first()
        if heartbeat:
            heartbeat.processed_total += 1
            session.add(heartbeat)


def time_to_datetime():
    from datetime import datetime

    return datetime.utcnow()


async def run_worker(stop_event: asyncio.Event) -> None:
    settings = get_settings()
    init_db()
    broker: BaseBroker
    if settings.environment == "test":
        broker = InMemoryBroker()
    else:
        redis = Redis.from_url(settings.redis_url, decode_responses=False)
        broker = RedisBroker(redis)
    context = WorkerContext(
        worker_id=os.getenv("GENESIS_WORKER_ID", "worker-1"),
        broker=broker,
        stop_event=stop_event,
    )
    runner = WorkerRunner(context)
    await runner.run()


def main() -> None:
    configure_logging()
    from .shutdown import run_with_graceful_shutdown

    run_with_graceful_shutdown(lambda stop_event: run_worker(stop_event))


if __name__ == "__main__":  # pragma: no cover
    main()
