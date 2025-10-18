"""Stats endpoints."""
from __future__ import annotations

import asyncio
import statistics
from typing import Any, Dict, List

from fastapi import APIRouter, Request
from sqlmodel import select

from ...db import get_session
from ...models import Job, JobState

router = APIRouter()


@router.get("/stats")
async def stats(request: Request) -> Dict[str, Any]:
    broker = request.app.state.broker
    depth = await broker.depth()

    def _collect() -> Dict[str, Any]:
        with get_session() as session:
            successes = session.exec(select(Job).where(Job.state == JobState.SUCCEEDED)).all()
            failures = session.exec(select(Job).where(Job.state == JobState.FAILED)).all()
            durations: List[float] = []
            for job in successes:
                if job.started_at and job.finished_at:
                    durations.append((job.finished_at - job.started_at).total_seconds())
            p50 = statistics.median(durations) if durations else 0.0
            p95 = statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else p50
            return {
                "queue_depth": depth,
                "success": len(successes),
                "failed": len(failures),
                "p50_duration": p50,
                "p95_duration": p95,
            }

    return await asyncio.to_thread(_collect)
