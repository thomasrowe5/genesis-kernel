from genesis.registry.manager import ModuleRegistryManager
from genesis.router.canary import CanaryController


def setup_registry() -> ModuleRegistryManager:
    return ModuleRegistryManager()


def test_canary_progression_and_rollback():
    registry = setup_registry()
    baseline = registry.register_version("fib", "v1", "path")
    baseline.reward_ma = 0.8
    baseline.p95_ms = 100.0
    baseline.error_rate = 0.05
    registry.activate_version(baseline)

    candidate = registry.register_version("fib", "v2", "path")
    candidate.reward_ma = 0.85
    candidate.p95_ms = 95.0
    candidate.error_rate = 0.04
    registry.start_canary("fib", "v2", 0.01)

    controller = CanaryController(registry)
    result = controller.step("fib")
    assert result == "progressed"
    updated_candidate = registry.get_version("fib", "v2")
    assert updated_candidate is not None and updated_candidate.traffic_share >= 0.05

    # Force breach
    updated_candidate.error_rate = 0.2
    rollback_result = controller.step("fib")
    assert rollback_result == "rollback"
    assert updated_candidate.canary is False
