from __future__ import annotations

import asyncio
import pytest
from genesis.evaluator.service import EvaluationResult, EvaluatorService
from genesis.optimizer.loop import OptimizerLoop
from genesis.registry.manager import ModuleRegistryManager


class StubEvaluator(EvaluatorService):
    def __init__(self, result: EvaluationResult) -> None:  # type: ignore[super-init-not-called]
        self._result = result

    async def evaluate_module(self, module: str, version: str, benchmark_name=None, overrides=None) -> EvaluationResult:  # type: ignore[override]
        return self._result


def make_registry() -> ModuleRegistryManager:
    try:
        from sqlmodel import Session, create_engine  # type: ignore

        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        ModuleRegistryManager.create_all(engine)
        session = Session(engine)
        return ModuleRegistryManager(session)
    except Exception:
        return ModuleRegistryManager()


def test_optimizer_promotes_stronger_candidate():
    registry = make_registry()
    try:
        evaluator = StubEvaluator(
            EvaluationResult(
                module="fibonacci",
                version="v2",
                metrics={"accuracy": 0.95, "latency": 0.2, "stability": 0.96},
                passed=True,
                metadata={},
                duration=0.2,
            )
        )
        loop = OptimizerLoop(registry, evaluator, replacement_delta=0.05)
        outcome = asyncio.run(
            loop.evaluate_candidate("fibonacci", "v2", "src/genesis/modules/fibonacci.py")
        )
        assert outcome.promoted is True
    finally:
        if registry.session:
            registry.session.close()


def test_optimizer_respects_threshold():
    registry = make_registry()
    try:
        # Seed with a strong baseline
        baseline = registry.register_version("sleep", "v1", "src/genesis/modules/sleep.py")
        registry.record_metrics(baseline, 0.9, {"accuracy": 0.95, "latency": 0.25, "stability": 0.97})
        registry.activate_version(baseline)

        evaluator = StubEvaluator(
            EvaluationResult(
                module="sleep",
                version="v2",
                metrics={"accuracy": 0.94, "latency": 0.24, "stability": 0.96},
                passed=True,
                metadata={},
                duration=0.24,
            )
        )
        loop = OptimizerLoop(registry, evaluator, replacement_delta=0.05)
        outcome = asyncio.run(
            loop.evaluate_candidate("sleep", "v2", "src/genesis/modules/sleep_v2.py")
        )
        assert outcome.promoted is False
    finally:
        if registry.session:
            registry.session.close()
