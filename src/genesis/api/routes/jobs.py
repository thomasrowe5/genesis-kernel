"""Job routes."""
from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from sqlmodel import select

from ...config import get_settings
from ...db import get_session
from ...models import Event, Job, JobState
from ...queues.schemas import EnqueueRequest, JobListResponse, JobPayload, JobResponse

router = APIRouter(prefix="/jobs")


def _job_to_response(job: Job) -> JobResponse:
    result = None
    if job.result_json:
        try:
            result = json.loads(job.result_json)
        except json.JSONDecodeError:
            result = job.result_json
    return JobResponse(
        id=job.id or 0,
        task_type=job.task_type,
        state=job.state,
        attempts=job.attempts,
        result=result,
        error=job.error_text,
    )


async def _get_or_create_job(payload: EnqueueRequest) -> Job:
    def _op() -> Job:
        with get_session() as session:
            if payload.dedupe_key:
                existing = session.exec(
                    select(Job)
                    .where(Job.dedupe_key == payload.dedupe_key)
                    .order_by(Job.created_at.desc())
                ).first()
                if existing:
                    return existing
            job = Job(
                task_type=payload.task_type,
                payload_json=json.dumps(payload.model_dump()),
                dedupe_key=payload.dedupe_key,
                priority=payload.priority,
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            session.add(Event(job_id=job.id, type="queued", data_json=job.payload_json))
            session.commit()
            return job

    return await asyncio.to_thread(_op)


@router.post("")
async def enqueue_job(request: Request, payload: EnqueueRequest) -> dict[str, Any]:
    job = await _get_or_create_job(payload)
    if job.state != JobState.QUEUED:
        return {"job_id": job.id}
    broker = request.app.state.broker
    message = JobPayload(task_type=payload.task_type, args=payload.args, kwargs=payload.kwargs)
    await broker.enqueue(
        job.id or 0,
        message,
        priority=payload.priority,
        dedupe_key=payload.dedupe_key,
        dedupe_ttl=get_settings().dedupe_ttl,
    )
    return {"job_id": job.id}


@router.get("/{job_id}")
async def get_job(job_id: int) -> JobResponse:
    def _fetch() -> Optional[Job]:
        with get_session() as session:
            return session.get(Job, job_id)

    job = await asyncio.to_thread(_fetch)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


@router.get("")
async def list_jobs(
    state: Optional[JobState] = Query(default=None),
    task_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> JobListResponse:
    def _fetch() -> JobListResponse:
        with get_session() as session:
            query = select(Job)
            if state:
                query = query.where(Job.state == state)
            if task_type:
                query = query.where(Job.task_type == task_type)
            jobs = session.exec(query).all()
            sliced = jobs[offset : offset + limit]
            return JobListResponse(jobs=[_job_to_response(job) for job in sliced], total=len(jobs))

    return await asyncio.to_thread(_fetch)
