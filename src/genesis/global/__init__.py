"""Compatibility wrappers for the planetary global modules.

The actual implementations live under :mod:`genesis.global_` to avoid Python's
``global`` keyword ambiguity.  This package re-exports those symbols so that the
expected import paths remain available to callers.
"""
from __future__ import annotations

from .. import global_ as _impl  # type: ignore[attr-defined]

GlobalIntelligence = _impl.intelligence.GlobalIntelligence
GlobalMetricSample = _impl.intelligence.GlobalMetricSample
GlobalAdaptationEngine = _impl.adaptation.GlobalAdaptationEngine
AdaptationGoal = _impl.adaptation.AdaptationGoal
PlanetarySimulation = _impl.simulation.PlanetarySimulation
SimulationScenario = _impl.simulation.SimulationScenario
SimulationResult = _impl.simulation.SimulationResult

__all__ = [
    "GlobalIntelligence",
    "GlobalMetricSample",
    "GlobalAdaptationEngine",
    "AdaptationGoal",
    "PlanetarySimulation",
    "SimulationScenario",
    "SimulationResult",
]
