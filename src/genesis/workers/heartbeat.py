"""Worker heartbeat management."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from sqlmodel import select

from ..db import get_session
from ..metrics import worker_heartbeat
from ..models import WorkerHeartbeat as WorkerHeartbeatModel


async def record_heartbeat(worker_id: str, interval: float, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        await asyncio.to_thread(_upsert_heartbeat, worker_id)
        worker_heartbeat.labels(worker_id=worker_id).set(datetime.utcnow().timestamp())
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue


def _upsert_heartbeat(worker_id: str) -> None:
    with get_session() as session:
        heartbeat: Optional[WorkerHeartbeatModel] = session.exec(
            select(WorkerHeartbeatModel).where(WorkerHeartbeatModel.worker_id == worker_id)
        ).first()
        if heartbeat is None:
            heartbeat = WorkerHeartbeatModel(worker_id=worker_id)
            session.add(heartbeat)
        heartbeat.last_seen_at = datetime.utcnow()
        session.add(heartbeat)
        session.commit()
