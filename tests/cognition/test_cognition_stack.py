from __future__ import annotations

import asyncio

import pytest
fastapi = pytest.importorskip("fastapi")
from fastapi import FastAPI
from fastapi.testclient import TestClient

from genesis.cognition import (
    ExperimentPlanner,
    PlannerContext,
    Reasoner,
    ReasoningRequest,
    ReportSummarizer,
    Theorist,
)
from genesis.knowledge import (
    EmbeddingRecord,
    EmbeddingStore,
    KnowledgeEdge,
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeNodeType,
    KnowledgeRelation,
    KnowledgeRetriever,
)
from genesis.research import (
    ExperimentReporter,
    ExperimentRunner,
    InMemoryExperimentStore,
)
from genesis.api.routes import cognition as cognition_routes


@pytest.fixture()
def knowledge_components() -> tuple[KnowledgeGraph, KnowledgeRetriever]:
    graph = KnowledgeGraph()
    embeddings = EmbeddingStore()
    module = KnowledgeNode(
        id="module-alpha",
        type=KnowledgeNodeType.MODULE,
        label="alpha",
        properties={"domain": "math"},
    )
    metric = KnowledgeNode(
        id="metric-reward",
        type=KnowledgeNodeType.METRIC,
        label="reward",
        properties={"baseline": 0.5},
    )
    experiment = KnowledgeNode(
        id="experiment-1",
        type=KnowledgeNodeType.EXPERIMENT,
        label="exp-1",
        properties={"reward": 0.8},
    )
    graph.add_node(module)
    graph.add_node(metric)
    graph.add_node(experiment)
    graph.add_edge(
        KnowledgeEdge(
            id="edge-alpha-reward",
            src_id=module.id,
            dst_id=metric.id,
            relation=KnowledgeRelation.IMPROVES,
            properties={},
        )
    )
    embeddings.add(EmbeddingRecord(node_id=module.id, vector=[1.0, 0.5, 0.25]))
    retriever = KnowledgeRetriever(graph, embeddings)
    return graph, retriever


async def _mock_evaluator(plan):
    await asyncio.sleep(0)
    return {metric: value + 0.1 for metric, value in plan.metrics.items()}


def test_planner_generates_plan(knowledge_components):
    graph, retriever = knowledge_components
    planner = ExperimentPlanner(graph, retriever)
    context = PlannerContext(goal="improve alpha", performance_gaps={"reward": 1.0}, prior_metrics={})
    plans = planner.propose(context)
    assert plans
    assert plans[0].goal == "improve alpha"
    assert "reward" in plans[0].metrics


def test_reasoner_and_theorist():
    reasoner = Reasoner()
    request = ReasoningRequest(
        module_a="alpha",
        module_b="beta",
        metric="reward",
        observations={"reward": {"alpha": 1.0, "beta": 0.5}},
    )
    response = reasoner.evaluate(request)
    assert "alpha" in response.statement
    theorist = Theorist()
    class DummyResult:
        def __init__(self):
            self.metrics = {"reward": 1.2}

    update = theorist.derive([DummyResult()])
    assert "reward" in update.statement


def test_summarizer_outputs_markdown(knowledge_components):
    graph, retriever = knowledge_components
    planner = ExperimentPlanner(graph, retriever)
    context = PlannerContext(goal="improve alpha", performance_gaps={"reward": 1.0}, prior_metrics={})
    plan = planner.propose(context)[0]
    runner = ExperimentRunner(_mock_evaluator)
    result = asyncio.run(runner.run(plan))
    reporter = ExperimentReporter()
    reporter.add_result(result)
    summarizer = ReportSummarizer()
    summary = summarizer.render(plan, result, ["alpha improves reward"])
    assert "Autonomous Research Report" in summary.content
    assert "alpha improves reward" in summary.content


def test_knowledge_retrieval(knowledge_components):
    graph, retriever = knowledge_components
    context = retriever.by_embedding([1.0, 0.5, 0.25], limit=1)
    assert context.nodes
    assert context.nodes[0].type == KnowledgeNodeType.MODULE


def test_api_integration(knowledge_components):
    graph, retriever = knowledge_components
    planner = ExperimentPlanner(graph, retriever)
    store = InMemoryExperimentStore()
    reporter = ExperimentReporter()
    summarizer = ReportSummarizer()
    runner = ExperimentRunner(_mock_evaluator)

    app = FastAPI()
    app.include_router(cognition_routes.router)
    app.dependency_overrides[cognition_routes.get_planner] = lambda: planner
    app.dependency_overrides[cognition_routes.get_store] = lambda: store
    app.dependency_overrides[cognition_routes.get_runner] = lambda: runner
    app.dependency_overrides[cognition_routes.get_reporter] = lambda: reporter
    app.dependency_overrides[cognition_routes.get_summarizer] = lambda: summarizer

    client = TestClient(app)
    response = client.post("/cognition/plan", json={"goal": "improve", "gaps": {"reward": 1.0}})
    assert response.status_code == 200
    plan_id = response.json()[0]["id"]

    response = client.post("/cognition/run", json={"plan_id": plan_id})
    assert response.status_code == 200
    reporter.record_insight("reward increased", {"reward": 1.1})

    response = client.get("/cognition/status")
    assert response.status_code == 200
    assert response.json()[0]["status"] == "completed"

    response = client.get("/cognition/insight")
    assert response.status_code == 200
    assert response.json()[0]["statement"] == "reward increased"

    response = client.get(f"/cognition/report/{plan_id}")
    assert response.status_code == 200
    assert "Experiment Report" in response.json()["content"]
