"""Tests covering the reflexive intelligence expansion (Phase 9)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest

from genesis.adaptation import AdaptationPlanner, ChangeValidator
from genesis.metacog import Introspector, ReflectionJournal, UncertaintyTracker
from genesis.reflexion import DigitalTwinBuilder, SimulationChange, TwinSimulator
from genesis.reflexion.simulator import SimulationResult
from genesis.registry.manager import ModuleRegistryManager


@pytest.fixture
def registry() -> ModuleRegistryManager:
    manager = ModuleRegistryManager()
    module = manager.register_version("optimizer", "v1", "path/optimizer.py")
    manager.record_metrics(module, 0.8, {"loss": 0.2})
    module2 = manager.register_version("router", "v2", "path/router.py")
    manager.record_metrics(module2, 0.5, {"latency": 0.1})
    return manager


@pytest.fixture
def twin_builder(registry: ModuleRegistryManager) -> DigitalTwinBuilder:
    return DigitalTwinBuilder(registry)


@pytest.fixture
def simulator(twin_builder: DigitalTwinBuilder) -> TwinSimulator:
    return TwinSimulator(twin_builder)


def _run(coro):
    return asyncio.run(coro)


def test_twin_snapshot_reproducible(twin_builder: DigitalTwinBuilder) -> None:
    snap1 = _run(twin_builder.build_snapshot())
    snap2 = _run(twin_builder.build_snapshot())
    assert snap1.metrics == snap2.metrics
    assert snap1.config == snap2.config
    assert sorted(snap1.topology["modules"], key=lambda m: (m["name"], m["version"])) == sorted(
        snap2.topology["modules"], key=lambda m: (m["name"], m["version"])
    )


def test_simulation_deterministic(simulator: TwinSimulator, twin_builder: DigitalTwinBuilder) -> None:
    base_state = _run(twin_builder.build_snapshot())
    change = SimulationChange(module="optimizer", param="learning_rate", value=0.9)
    result1 = _run(simulator.run(change, base_state=base_state))
    result2 = _run(simulator.run(change, base_state=base_state))
    assert result1.predicted_delta == result2.predicted_delta
    assert result1.seed == result2.seed


def test_introspector_detects_drift(twin_builder: DigitalTwinBuilder) -> None:
    tracker = UncertaintyTracker()
    introspector = Introspector(tracker=tracker, drift_threshold=0.0)
    snapshot = _run(twin_builder.build_snapshot())
    change = SimulationChange(module="optimizer", param="learning_rate", value=0.9)
    simulation = SimulationResult(
        change=change,
        predicted_delta={next(iter(snapshot.metrics)): 0.25},
        confidence=0.6,
        seed=1,
        generated_at=datetime.utcnow(),
    )
    report = introspector.evaluate(
        snapshot,
        simulation=simulation,
        observed_metrics={next(iter(snapshot.metrics)): 0.0},
    )
    assert report.anomalies
    assert report.halt


def test_planner_blocks_low_confidence(
    twin_builder: DigitalTwinBuilder, simulator: TwinSimulator
) -> None:
    tracker = UncertaintyTracker()
    introspector = Introspector(tracker=tracker, drift_threshold=0.0, min_confidence=0.2)
    journal = ReflectionJournal()
    validator = ChangeValidator(min_confidence=0.0)
    planner = AdaptationPlanner(
        twin_builder=twin_builder,
        simulator=simulator,
        introspector=introspector,
        validator=validator,
        journal=journal,
    )
    change = SimulationChange(module="optimizer", param="learning_rate", value=0.7)
    decision = _run(planner.plan(change))
    assert not decision.validation.accepted


def test_reflection_log_consistency() -> None:
    journal = ReflectionJournal()
    entry = journal.record(
        reason="test",
        prediction={"metric": 0.5},
        result={"metric": 0.6},
        delta={"metric": 0.1},
        confidence=0.7,
    )
    logs = journal.query(since=datetime.utcnow() - timedelta(minutes=1))
    assert logs and logs[-1].reason == entry.reason
    assert logs[-1].prediction["metric"] == pytest.approx(0.5)
