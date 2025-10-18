import asyncio

from starlette.requests import Request

from genesis.api.routes.jobs import enqueue_job
from genesis.metrics import job_duration, jobs_completed, jobs_enqueued, queue_depth
from genesis.queues.schemas import EnqueueRequest
from genesis.workers.runner import WorkerContext, WorkerRunner


async def _request(app, path: str) -> Request:
    async def receive() -> dict:
        return {"type": "http.request"}

    scope = {"type": "http", "app": app, "method": "POST", "path": path}
    return Request(scope, receive)


def test_metrics_flow(app):
    loop = asyncio.get_event_loop()
    start_enqueued = jobs_enqueued._value.get()
    start_completed = jobs_completed.labels(status="succeeded")._value.get()
    request = loop.run_until_complete(_request(app, "/jobs"))
    payload = EnqueueRequest(task_type="sleep", args=[], kwargs={"seconds": 0})
    loop.run_until_complete(enqueue_job(request, payload))
    assert jobs_enqueued._value.get() >= start_enqueued + 1
    broker = app.state.broker
    message = loop.run_until_complete(broker.dequeue(timeout=0))
    runner = WorkerRunner(WorkerContext(worker_id="metrics", broker=broker, stop_event=asyncio.Event()))
    loop.run_until_complete(runner._process_message(message))
    assert jobs_completed.labels(status="succeeded")._value.get() >= start_completed + 1
    assert job_duration._sum.get() >= 0.0
    assert queue_depth._value.get() == 0
