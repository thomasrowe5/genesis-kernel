"""Planner coordinating simulations and validations before rollout."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from genesis.metacog.introspector import Introspector, IntrospectionReport
from genesis.metacog.reflection import ReflectionJournal
from genesis.metacog.selfquery import SelfQueryService
from genesis.reflexion.predictor import ReflexivePredictor
from genesis.reflexion.simulator import SimulationChange, TwinSimulator
from genesis.reflexion.twin import DigitalTwinBuilder

from .sandbox import AdaptationSandbox
from .validator import ChangeValidator, ValidationOutcome


@dataclass(slots=True)
class PlanningDecision:
    change: SimulationChange
    simulation: SimulationResult
    introspection: IntrospectionReport
    validation: ValidationOutcome


class AdaptationPlanner:
    """Decide whether to promote simulated strategies into production."""

    def __init__(
        self,
        twin_builder: DigitalTwinBuilder,
        simulator: TwinSimulator,
        introspector: Introspector,
        validator: ChangeValidator,
        journal: ReflectionJournal,
        predictor: Optional[ReflexivePredictor] = None,
        self_query: Optional[SelfQueryService] = None,
    ) -> None:
        self._builder = twin_builder
        self._simulator = simulator
        self._introspector = introspector
        self._validator = validator
        self._journal = journal
        self._predictor = predictor or ReflexivePredictor()
        self._self_query = self_query
        self._sandbox = AdaptationSandbox(twin_builder)

    async def plan(self, change: SimulationChange) -> PlanningDecision:
        snapshot = await self._builder.build_snapshot()
        if self._self_query is not None:
            self._self_query.update_snapshot(snapshot)
        simulation = await self._simulator.run(change, base_state=snapshot)
        self._predictor.observe(simulation)
        async with self._sandbox.run(change, base_state=snapshot) as sandbox_state:
            observed_metrics = sandbox_state.metrics
        report = self._introspector.evaluate(snapshot, simulation=simulation, observed_metrics=observed_metrics)
        validation = self._validator.validate(report, simulation)

        delta = simulation.predicted_delta
        self._journal.record(
            reason=f"simulation:{change.module}:{change.param}",
            prediction=simulation.predicted_delta,
            result={},
            delta=delta,
            confidence=report.confidence,
        )

        if self._self_query is not None:
            self._self_query.update_snapshot(snapshot)

        return PlanningDecision(
            change=change,
            simulation=simulation,
            introspection=report,
            validation=validation,
        )
