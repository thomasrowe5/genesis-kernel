from genesis.optimizer.online import OnlineOptimizer, Outcome
from genesis.registry.manager import ModuleRegistryManager
from genesis.router.router import PromptRouter


def test_online_optimizer_updates_reward_and_params():
    registry = ModuleRegistryManager()
    baseline = registry.register_version("fib", "v1", "path")
    baseline.params_json = {"lr": 0.1}
    registry.activate_version(baseline)

    router = PromptRouter(registry, policy="round_robin", rng_seed=1)
    optimizer = OnlineOptimizer(registry, router, target_latency_ms=200.0)

    outcome = Outcome(module="fib", version="v1", score=0.9, latency_ms=150.0, success=True)
    reward = optimizer.update(outcome)
    assert reward > 0
    updated = registry.get_version("fib", "v1")
    assert updated is not None
    assert updated.reward_ma > 0
    assert "lr" in updated.params_json
