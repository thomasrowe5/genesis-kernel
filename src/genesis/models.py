"""Database models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEAD_LETTER = "dead-letter"


class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_type: str
    payload_json: str
    state: JobState = Field(default=JobState.QUEUED)
    attempts: int = Field(default=0)
    dedupe_key: Optional[str] = None
    priority: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result_json: Optional[str] = None
    error_text: Optional[str] = None


class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id")
    type: str
    at: datetime = Field(default_factory=datetime.utcnow)
    data_json: Optional[str] = None


class WorkerHeartbeat(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    worker_id: str
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)
    in_flight: int = Field(default=0)
    processed_total: int = Field(default=0)
