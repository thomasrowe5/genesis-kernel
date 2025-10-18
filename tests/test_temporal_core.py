"""Tests covering the temporal recursion components."""
from __future__ import annotations

import asyncio

import pytest

from genesis.temporal import (
    TemporalBranchManager,
    TemporalObserver,
    TemporalViolation,
    TemporalRecursionScheduler,
    TemporalReconciler,
    TimelineManager,
)
from genesis.temporal.recursion import RecursionResult
from genesis.chronos import ContinuityEnforcer


def test_timeline_vector_clock_monotonic() -> None:
    timeline = TimelineManager(node_id="genesis")
    first = timeline.record_commit({"metrics": {"a": 1.0}})
    second = timeline.record_commit({"metrics": {"a": 2.0}})

    assert first.vector_clock["genesis"] == 1
    assert second.vector_clock["genesis"] == 2
    assert timeline.list_commits()[-1].id == second.id


def test_recursion_scheduler_runs() -> None:
    timeline = TimelineManager(node_id="genesis")
    commit = timeline.record_commit({"metrics": {"a": 1.0, "b": 2.0}})
    observer = TemporalObserver(entropy_limit=5.0)
    scheduler = TemporalRecursionScheduler(timeline, observer)

    async def simulator(state):
        metrics = dict(state["metrics"])
        metrics["a"] += 0.1
        return {"metrics": metrics}

    result = asyncio.run(scheduler.run_from_commit(commit.id, simulator))
    assert isinstance(result, RecursionResult)
    assert result.run.status == "success"
    projection = scheduler.materialize_projection(result)
    assert projection.id is not None
    assert projection.vector_clock["genesis"] == 2


def test_branch_merge_with_continuity() -> None:
    timeline = TimelineManager(node_id="genesis")
    commit = timeline.record_commit({"metrics": {"a": 1.0}})
    enforcer = ContinuityEnforcer(["Prime Ethic"])
    reconciler = TemporalReconciler(enforcer)
    branches = TemporalBranchManager(timeline, enforcer)

    branch = branches.create_branch(commit.id, {"metrics": {"a": 1.0}}, name="beta")
    report = reconciler.reconcile({"metrics": {"a": 1.0}}, commit.state_json)
    merged = branches.merge_branch(branch.id, report)

    assert merged.merged is True
    assert pytest.approx(report.score) == 1.0


def test_observer_entropy_violation() -> None:
    observer = TemporalObserver(entropy_limit=0.0)
    with pytest.raises(TemporalViolation):
        observer.observe({"metrics": {"a": 1.0}}, {"metrics": {"a": 1.0, "b": 2.0}}, context="test")


def test_reconciler_consistency_score() -> None:
    enforcer = ContinuityEnforcer([])
    reconciler = TemporalReconciler(enforcer)
    baseline = {"metrics": {"a": 1.0, "b": 2.0}}
    report = reconciler.reconcile(baseline, baseline)
    assert report.delta == 0.0
    assert report.score == 1.0
