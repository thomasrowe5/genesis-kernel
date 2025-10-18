import asyncio

from starlette.requests import Request

from genesis.api.routes.jobs import enqueue_job, get_job
from genesis.models import JobState
from genesis.queues.schemas import EnqueueRequest
from genesis.workers.runner import WorkerContext, WorkerRunner


async def _request(app, path: str) -> Request:
    async def receive() -> dict:
        return {"type": "http.request"}

    scope = {"type": "http", "app": app, "method": "POST", "path": path}
    return Request(scope, receive)


def test_enqueue_execute(app):
    loop = asyncio.get_event_loop()
    request = loop.run_until_complete(_request(app, "/jobs"))
    payload = EnqueueRequest(task_type="fibonacci", args=[5], kwargs={})
    result = loop.run_until_complete(enqueue_job(request, payload))
    job_id = result["job_id"]
    broker = app.state.broker
    message = loop.run_until_complete(broker.dequeue(timeout=0))
    assert message is not None
    runner = WorkerRunner(WorkerContext(worker_id="test", broker=broker, stop_event=asyncio.Event()))
    loop.run_until_complete(runner._process_message(message))
    response = loop.run_until_complete(get_job(job_id))
    assert response.state == JobState.SUCCEEDED
    assert response.result == 5
