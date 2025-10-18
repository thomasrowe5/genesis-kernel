"""Prometheus metrics helpers."""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

jobs_enqueued = Counter("genesis_jobs_enqueued_total", "Total jobs enqueued", [])
jobs_completed = Counter(
    "genesis_jobs_completed_total", "Total jobs completed", ["status"]
)
job_duration = Histogram(
    "genesis_job_duration_seconds",
    "Duration of job execution",
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60),
)
queue_depth = Gauge("genesis_queue_depth", "Number of jobs waiting in the queue")
worker_heartbeat = Gauge(
    "genesis_worker_heartbeat",
    "Worker heartbeat timestamps",
    ["worker_id"],
)


instrumentator = Instrumentator()


def setup_metrics(app) -> None:
    if not instrumentator.instrumentations:
        instrumentator.instrument(app)
    instrumentator.expose(app, endpoint="/metrics")
