"""Unit tests for governance, provenance, and cluster primitives."""
from __future__ import annotations

from pathlib import Path

import pytest

from genesis.cluster.scheduler import ConsistentHashScheduler, SchedulerAssignment
from genesis.governance.policy import PolicyEngine, PolicyRule, ResourceUsage
from genesis.governance.rbac import RBACManager
from genesis.governance.signer import ModuleSigner
from genesis.metrics import (
    genesis_provenance_edges_total,
    genesis_signature_verifications_total,
)
from genesis.provenance.graph import ProvenanceGraph
from genesis.provenance.lineage import GraphExporter, GraphImporter


def test_consistent_hash_scheduler_assignment() -> None:
    scheduler = ConsistentHashScheduler(replicas=10)
    scheduler.configure(
        [
            SchedulerAssignment(node_id="node-a", weight=1.0),
            SchedulerAssignment(node_id="node-b", weight=1.0),
        ]
    )
    node = scheduler.assign("job-123")
    assert node in {"node-a", "node-b"}


def test_provenance_export_import(tmp_path: Path) -> None:
    graph = ProvenanceGraph()
    graph.add_node("Job", "job-1", name="demo")
    graph.add_node("ModuleVersion", "module:v1")
    graph.add_edge("Job", "job-1", "ModuleVersion", "module:v1", "used")
    initial_edges = genesis_provenance_edges_total._value.get()  # type: ignore[attr-defined]
    path = tmp_path / "graph.jsonl"
    GraphExporter(path).export(graph)
    imported = GraphImporter(path).import_graph()
    assert list(imported.edges())
    assert genesis_provenance_edges_total._value.get() >= initial_edges  # type: ignore[attr-defined]


def test_policy_engine_detects_violation() -> None:
    engine = PolicyEngine([PolicyRule(id="cpu", name="CPU", type="cpu", threshold=50.0)])
    usage = ResourceUsage(cpu_percent=75.0, memory_mb=100.0, network_io_mb=1.0, evals_running=1, compute_seconds=10.0)
    events = engine.evaluate(usage)
    assert events and events[0].rule_id == "cpu"


def test_signature_sign_and_verify(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text("print('hello world')", encoding="utf-8")
    secret = b"super-secret"
    signer = ModuleSigner(secret=secret)
    record = signer.sign("module:v1", module_path, "{}", signer="tester")
    assert signer.verify(record, module_path, "{}")
    metric = genesis_signature_verifications_total.labels(status="success")._value.get()  # type: ignore[attr-defined]
    assert metric >= 1


def test_rbac_authorisation() -> None:
    manager = RBACManager()
    manager.register_key("test", "secret", roles=["admin"])
    principal = manager.authorise("test", "secret", role="admin")
    assert "admin" in principal.roles
    with pytest.raises(Exception):
        manager.authorise("test", "secret", role="viewer")
