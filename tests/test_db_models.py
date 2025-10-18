from genesis.db import get_session
from genesis.models import Event, Job, JobState


def test_job_persistence():
    with get_session() as session:
        job = Job(task_type="sleep", payload_json="{}")
        session.add(job)
        session.commit()
        session.refresh(job)
        assert job.state == JobState.QUEUED
        event = Event(job_id=job.id, type="queued")
        session.add(event)
        session.commit()
        assert event.id is not None
