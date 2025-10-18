# Provenance, Replay, and Governance

## Provenance Graph

Genesis captures experiment provenance as a directed acyclic graph (DAG). Nodes
represent Jobs, ModuleVersions, Evaluations, and PolicyEvents. Edges describe
relationships such as `used`, `produced`, and `governed_by`.

Example JSON fragment produced by `GraphExporter`:

```json
{
  "src_type": "Job",
  "src_id": "experiment-42",
  "dst_type": "ModuleVersion",
  "dst_id": "fibonacci:v2",
  "relation": "used",
  "metadata": {"reward": 0.98}
}
```

## Replay

Deterministic replay relies on `ReplayEngine` which registers asynchronous
executors keyed by experiment identifier. When the `/cluster/replay` endpoint or
`genesis replay --experiment <id>` CLI command triggers a replay, the engine
executes the stored executor, hashes the output payload, and returns the digest.
The metric `genesis_replay_runs_total` tracks invocation volume.

ASCII sequence for replay:

```
User CLI        Cluster API        Replay Engine
   |                |                    |
   |-- POST /replay -------------------->|
   |                |-- run executor --->|
   |                |<-- hash digest ----|
   |<-- 200 {hash} ----------------------|
```

## Governance Policies

Policies are described by `PolicyRule` objects. The `PolicyEngine` evaluates
resource usage snapshots and emits `PolicyEvent` instances when thresholds are
exceeded. The `ComplianceChecker` integrates with `ClusterNodeService` to record
violations via the `genesis_policy_violations_total` metric.

| Policy Type | Metric Source        | Threshold Example | Action                |
|-------------|----------------------|-------------------|-----------------------|
| cpu         | Prometheus gauges    | 75%               | Log violation         |
| memory      | Node telemetry       | 4096 MB           | Alert & throttle      |
| network     | Runtime statistics   | 500 MB            | Alert only            |
| evals       | Evaluator scheduler  | 10 concurrent     | Queue new jobs        |
| compute_seconds | Usage ledger     | 3600 per hour     | Pause offending node  |

## Compliance Flow

1. Collect resource usage from node metrics.
2. Feed snapshot into `ComplianceChecker.evaluate`.
3. Emit `PolicyEvent` records for violations.
4. Persist to SQLModel tables `PolicyRule` and `PolicyEvent` for audit.
5. Push aggregated counts to Prometheus for dashboards.

## Governance Storage Tables

- **ClusterNode**: Node registration, leader flags, and heartbeat data.
- **PolicyRule**: Declarative policy definitions.
- **PolicyEvent**: Historical compliance alerts.
- **Signature**: Module signature lineage and verification state.
- **ProvenanceEdge**: Materialized edges for audit queries.
