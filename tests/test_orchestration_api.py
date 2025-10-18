import pytest

fastapi = pytest.importorskip("fastapi")

FastAPI = fastapi.FastAPI
TestClient = pytest.importorskip("fastapi.testclient").TestClient

from genesis.api.routes import cache as cache_routes
from genesis.api.routes import orchestration
from genesis.registry.manager import ModuleRegistryManager
from genesis.router.cache import InMemoryCache
from genesis.router.router import PromptRouter


def build_registry() -> ModuleRegistryManager:
    registry = ModuleRegistryManager()
    baseline = registry.register_version("fib", "v1", "path")
    baseline.reward_ma = 0.8
    baseline.p95_ms = 100.0
    baseline.error_rate = 0.05
    baseline.params_json = {"lr": 0.1}
    registry.activate_version(baseline)
    return registry


def test_orchestration_endpoints():
    registry = build_registry()
    router = PromptRouter(registry, policy="round_robin", rng_seed=3)
    cache = InMemoryCache(default_ttl=10)

    app = FastAPI()
    app.include_router(orchestration.router)
    app.include_router(cache_routes.router)

    app.dependency_overrides[orchestration.get_registry_manager] = lambda: registry
    app.dependency_overrides[orchestration.get_prompt_router] = lambda: router
    app.dependency_overrides[cache_routes.get_cache] = lambda: cache

    client = TestClient(app)

    resp = client.post("/orchestrate/route", json={"task_type": "fib", "args": [1, 2], "kwargs": {}})
    assert resp.status_code == 200
    data = resp.json()
    assert data["module"] == "fib"

    registry.register_version("fib", "v2", "path")
    registry.get_version("fib", "v2").reward_ma = 0.85
    registry.get_version("fib", "v2").p95_ms = 90.0
    registry.get_version("fib", "v2").error_rate = 0.04
    resp = client.post(
        "/orchestrate/canary",
        json={"module": "fib", "candidate_version": "v2", "initial_share": 0.01},
    )
    assert resp.status_code == 200

    status_resp = client.get("/orchestrate/status", params={"module": "fib"})
    assert status_resp.status_code == 200
    assert any(v["version"] == "v2" for v in status_resp.json()["versions"])

    rollback_resp = client.post(
        "/orchestrate/rollback",
        json={"module": "fib", "version": "v2", "reason": "test"},
    )
    assert rollback_resp.status_code == 200

    cache.invalidate()
    client.get("/cache/keys")
