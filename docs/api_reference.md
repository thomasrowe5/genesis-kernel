# Genesis Unified API Reference (v1.0.1)

The FastAPI gateway defined in `src/genesis/api/main.py` exposes every subsystem under a consistent RBAC policy and metrics middleware. The OpenAPI schema regenerates automatically at runtime and is available at `/openapi.json`. Swagger UI is reachable at `/docs` and ReDoc at `/redoc`.

## Authentication

All endpoints require a bearer token header `Authorization: Bearer <key_id>:<secret>` unless explicitly noted. Role enforcement is performed by `genesis.governance.rbac.require_role` and maps to entries in `src/genesis/governance/policies.json`.

## Core Domain (`/core`)

| Method | Path | Description | Parameters |
|--------|------|-------------|------------|
| GET | `/core/modules/leaderboard` | Return top scoring module variants. | Query: `limit` (int, default 10). |
| DELETE | `/core/cache` | Flush cache entries. | Query: `task` (str, optional task prefix). |
| GET | `/core/cache/keys` | List cache keys optionally filtered by prefix. | Query: `prefix` (str, optional). |

### Example

```http
GET /core/modules/leaderboard?limit=5 HTTP/1.1
Authorization: Bearer local-admin:local-secret
```

Response:

```json
[
  {"module": "fibonacci", "version": "v3", "score": 0.991},
  {"module": "summation", "version": "v5", "score": 0.984}
]
```

## Cognition Domain (`/cognition`)

| Method | Path | Description | Body / Params |
|--------|------|-------------|---------------|
| POST | `/cognition/cognition/plan` | Generate experiment plans from a goal and gaps. | JSON: `{ "goal": str, "gaps": {metric: float}, "prior_metrics": {metric: [float]}, "limit": int }`. |
| POST | `/cognition/cognition/run` | Execute a previously generated plan. | JSON: `{ "plan_id": str }`. |
| GET | `/cognition/cognition/status` | List plan statuses with completion info. | None. |
| GET | `/cognition/cognition/insight` | Return derived insights with confidence. | None. |
| GET | `/cognition/cognition/report/{plan_id}` | Produce report summary for completed plan. | Path: `plan_id` (str). |

### Sample Payload

```json
{
  "goal": "reduce latency",
  "gaps": {"latency_p95": 20.0},
  "limit": 2
}
```

## Reflexion Domain (`/reflexion`)

| Method | Path | Description | Notes |
|--------|------|-------------|-------|
| GET | `/reflexion/reflexion/twin/state` | Build current digital twin snapshot. | Returns `TwinState` model. |
| POST | `/reflexion/reflexion/simulate/change` | Run hypothetical change through simulator. | Body: `SimulationChange` structure. |
| GET | `/reflexion/reflexion/reflection/logs` | Query reflection journal entries. | Query: `since` (ISO timestamp, optional), `limit` (int, default 50). |
| GET | `/reflexion/reflexion/uncertainty` | Export uncertainty tracker metrics. | Returns global confidence + metric list. |

## Temporal Domain (`/temporal`)

| Method | Path | Description | Body / Params |
|--------|------|-------------|---------------|
| POST | `/temporal/temporal/timeline/snapshot` | Persist state snapshot into timeline. | JSON: `{ "state": {}, "node_id": str?, "timestamp": datetime? }`. |
| POST | `/temporal/temporal/recursion/run` | Execute retrocausal recursion from commit. | JSON: `{ "commit_id": int, "label": str? }`. |
| GET | `/temporal/temporal/branch/list` | List active temporal branches. | None. |
| POST | `/temporal/temporal/branch/merge` | Merge branch with actual state using reconciler. | JSON: `{ "branch_id": int, "actual_state": {} }`. |
| GET | `/temporal/temporal/continuity/status` | Retrieve continuity metrics and alerts. | None. |

## Governance Domain (`/governance`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/governance/provenance/graph` | Return provenance DAG for artefacts. |
| POST | `/governance/provenance/export` | Export provenance bundle to signed payload. |
| POST | `/governance/provenance/replay` | Replay recorded artefact history for validation. |

## Router & Federation Domain (`/router`)

Routes combine orchestration and federation controls.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/router/orchestration/route` | Route candidate module traffic with canary weights. |
| POST | `/router/orchestration/canary` | Schedule canary rollout for module. |
| POST | `/router/orchestration/traffic` | Adjust live traffic weights. |
| GET | `/router/orchestration/status` | Report optimiser / router health snapshot. |
| POST | `/router/orchestration/rollback` | Initiate rollback to previous stable version. |
| POST | `/router/federation/peer` | Register or update peer federation profile. |
| GET | `/router/federation/peers` | List connected peers. |
| POST | `/router/federation/proposal` | Submit governance proposal for voting. |
| POST | `/router/federation/vote` | Vote on outstanding proposal. |
| GET | `/router/federation/ledger` | Inspect federation ledger entries. |

## Cosmic & Metanet Domain (`/cosmic`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/cosmic/cosmic/seed/deploy` | Deploy a cosmic seed and return handle. |
| GET | `/cosmic/cosmic/seed/status/{seed_id}` | Check deployment status for seed. |
| GET | `/cosmic/cosmic/metrics` | Export cosmic network telemetry. |
| POST | `/cosmic/cosmic/sync` | Initiate global sync across seeds. |
| GET | `/cosmic/metanet/federations` | List metanet federations with treaty status. |
| POST | `/cosmic/metanet/treaty` | Propose or update federation treaty. |
| POST | `/cosmic/metanet/exchange` | Execute inter-federation exchange. |
| GET | `/cosmic/metanet/global_metrics` | View aggregated metanet metrics. |
| POST | `/cosmic/metanet/adapt` | Trigger global adaptation plan. |
| (Cluster) | `/cosmic/cluster/*` | Cluster routes surfaced from `genesis.cluster.node.router`. |

## Health & Telemetry

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health/live` | Liveness probe (requires `viewer` role). |
| GET | `/health/ready` | Readiness probe with dependency detail. |
| GET | `/metrics` | Prometheus scrape endpoint (anonymous). |

## Example Session

```bash
# Generate plan and run via API
curl -X POST "http://localhost:8000/cognition/cognition/plan" \
  -H "Authorization: Bearer local-admin:local-secret" \
  -H "Content-Type: application/json" \
  -d '{"goal": "increase throughput", "gaps": {"throughput": 15}, "limit": 1}'

curl -X GET "http://localhost:8000/temporal/temporal/continuity/status" \
  -H "Authorization: Bearer local-admin:local-secret"
```

All responses include trace metadata headers `x-trace-id` and `x-genesis-uptime` provided by the metrics middleware for end-to-end observability.
