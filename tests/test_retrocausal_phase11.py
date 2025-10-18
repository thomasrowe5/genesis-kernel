import pytest

pytest.importorskip("fastapi")

from genesis.api.routes import retrocausal as retro_routes
from genesis.metrics import (
    genesis_paradox_preventions_total,
    genesis_retro_consistency_score,
)
from genesis.multiverse import BranchState, MultiverseCoherenceEngine, MultiverseManifold, MultiverseObserver
from genesis.retrocausal import (
    RetroConsistencyVerifier,
    RetroPolicyUpdate,
    RetrocausalBridge,
    RetrocausalInferenceEngine,
    ReverseIntervention,
    ReverseSimulationRequest,
    ReverseSimulationResult,
    ReverseSimulator,
    TimelineCommit,
    TimelineRepository,
)


def build_components() -> dict[str, object]:
    timeline = TimelineRepository(
        [
            TimelineCommit("c1", reward=0.7, entropy=0.25, payload={"reward": 0.7}),
            TimelineCommit("c2", reward=0.75, entropy=0.22, payload={"reward": 0.75}),
            TimelineCommit("c3", reward=0.82, entropy=0.18, payload={"reward": 0.82}),
        ]
    )
    simulator = ReverseSimulator(timeline)
    inference = RetrocausalInferenceEngine(simulator, learning_rate=0.3)
    verifier = RetroConsistencyVerifier(tolerance=0.05)
    bridge = RetrocausalBridge(simulator, inference, verifier)
    manifold = MultiverseManifold(
        [
            BranchState("prime", {"reward": 0.82, "entropy": 0.18}),
            BranchState("divergent", {"reward": 0.68, "entropy": 0.28}),
            BranchState("stability", {"reward": 0.78, "entropy": 0.2}),
        ]
    )
    engine = MultiverseCoherenceEngine(manifold, epsilon=0.25)
    observer = MultiverseObserver(manifold, threshold=0.22)
    return {
        "timeline": timeline,
        "simulator": simulator,
        "inference": inference,
        "verifier": verifier,
        "bridge": bridge,
        "manifold": manifold,
        "engine": engine,
        "observer": observer,
    }


@pytest.mark.asyncio
async def test_reverse_simulation_reconstructs_forward_state():
    context = build_components()
    simulator = context["simulator"]
    timeline = context["timeline"]
    request = ReverseSimulationRequest(from_commit="c1", to_commit="c3")
    result = await simulator.run(request)
    assert list(result.path) == ["c1", "c2", "c3"]
    commits = timeline.between("c1", "c3")
    start_reward = commits[0].reward
    final_reward = commits[-1].reward
    assert pytest.approx(start_reward + result.reward_delta) == final_reward
    assert pytest.approx(result.entropy_delta) == commits[-1].entropy - commits[0].entropy
    assert result.interventions[-1].reward_adjustment == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_consistency_proof_validation_and_metrics():
    context = build_components()
    bridge = context["bridge"]
    verifier = context["verifier"]
    request = ReverseSimulationRequest(from_commit="c1", to_commit="c3")
    report = await bridge.execute(request)
    assert report.proof.valid is True
    assert verifier.chain() == report.proof.run_hash
    assert genesis_retro_consistency_score._value.get() == 1.0


@pytest.mark.asyncio
async def test_multiverse_merge_reduces_divergence():
    context = build_components()
    engine = context["engine"]
    manifold = context["manifold"]
    matrix_before = manifold.divergence_matrix()
    mean_before = sum(matrix_before.values()) / len(matrix_before)
    report = await engine.merge()
    matrix_after = manifold.divergence_matrix()
    mean_after = sum(matrix_after.values()) / len(matrix_after)
    assert mean_after < mean_before
    assert report.coherence_score >= 0.0


def test_paradox_prevention_triggers_for_invalid_update():
    verifier = RetroConsistencyVerifier(tolerance=0.01)
    result = ReverseSimulationResult(
        path=["c1"],
        reward_delta=0.1,
        entropy_delta=0.0,
        interventions=[ReverseIntervention("c1", reward_adjustment=0.0, entropy_adjustment=0.0, rationale="test")],
    )
    update = RetroPolicyUpdate(gradients={"c1": 1.0}, reward_delta=0.1, entropy_delta=0.0)
    before = genesis_paradox_preventions_total._value.get()
    proof = verifier.verify(result, update)
    assert proof.valid is False
    assert genesis_paradox_preventions_total._value.get() == before + 1


def test_retrocausal_api_endpoints_roundtrip():
    fastapi = pytest.importorskip("fastapi")
    TestClient = pytest.importorskip("fastapi.testclient").TestClient
    context = build_components()
    app = fastapi.FastAPI()
    app.include_router(retro_routes.router)
    app.dependency_overrides[retro_routes.get_bridge] = lambda: context["bridge"]
    app.dependency_overrides[retro_routes.get_verifier] = lambda: context["verifier"]
    app.dependency_overrides[retro_routes.get_coherence_engine] = lambda: context["engine"]
    client = TestClient(app)

    simulate_resp = client.post("/retrocausal/simulate", json={"from_commit": "c1", "to_commit": "c3"})
    assert simulate_resp.status_code == 200
    proof_hash = simulate_resp.json()["proof"]["hash"]

    consistency_resp = client.get("/retrocausal/consistency")
    assert consistency_resp.status_code == 200
    assert consistency_resp.json()["latest_hash"] == proof_hash

    state_resp = client.get("/retrocausal/multiverse/state")
    assert state_resp.status_code == 200
    assert "branches" in state_resp.json()

    merge_resp = client.post("/retrocausal/multiverse/merge", json={})
    assert merge_resp.status_code == 200
    assert merge_resp.json()["coherence_score"] >= 0.0


@pytest.mark.asyncio
async def test_multiverse_observer_flags_divergence():
    context = build_components()
    observer = context["observer"]
    alerts = observer.scan()
    assert any(alert.branch_b == "divergent" for alert in alerts)
