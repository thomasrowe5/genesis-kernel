"""Queue payload schemas."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..models import JobState


class JobPayload(BaseModel):
    task_type: str
    args: List[Any] = Field(default_factory=list)
    kwargs: Dict[str, Any] = Field(default_factory=dict)


class EnqueueRequest(BaseModel):
    task_type: str
    args: List[Any] = Field(default_factory=list)
    kwargs: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 0
    dedupe_key: Optional[str] = None


class JobResponse(BaseModel):
    id: int
    task_type: str
    state: JobState
    attempts: int
    result: Optional[Any]
    error: Optional[str]


class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
