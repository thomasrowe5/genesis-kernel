# Genesis Operations Manual (v1.0.1)

This manual documents the supported deployment, monitoring, and troubleshooting flows for the Genesis Perfection Build. The release unifies all runtime components under a single Makefile entry point and a typed configuration surface exposed by `GenesisSettings`.

## Prerequisites

- Python 3.11 with Poetry (`pipx install poetry`)
- Docker & Docker Compose (for the local demo stack)
- Redis 7.x and Postgres 14+ container images available locally
- Access to Prometheus / Grafana dashboards for observability

## Environment Configuration

All runtime settings derive from environment variables prefixed with `GENESIS_`. Common overrides include:

```bash
export GENESIS_ENVIRONMENT=staging
export GENESIS_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/genesis
export GENESIS_REDIS_URL=redis://localhost:6379/0
export GENESIS_WORKER_CONCURRENCY=8
export GENESIS_LOGGING_LEVEL=INFO
export GENESIS_OBSERVABILITY_PROMETHEUS_PORT=9000
```

Configuration is resolved by `GenesisSettings.from_env`, ensuring parity between CLI tooling, workers, and the FastAPI gateway.

## Lifecycle Commands

| Action | Command | Notes |
|--------|---------|-------|
| Install dependencies | `make install` | Installs the locked Poetry environment. |
| Start local stack | `make demo` | Brings up API, worker, Redis, Postgres, and Prometheus via `poetry run genesis deploy local`. |
| Run benchmark suite | `make benchmark` | Executes deterministic workloads and writes artefacts to `benchmarks/`. |
| Generate documentation | `make docs` | Builds the MkDocs site into `site/`. |
| Capture diagnostics | `poetry run genesis diag --output diagnostics.json` | Snapshots metrics, config, and timeline metadata. |
| Live metrics snapshot | `poetry run genesis diag` | Prints the latest uptime and key `genesis_*` counters to stdout. |

To enqueue and observe a sample optimisation workflow once the stack is live:

```bash
poetry run genesis plan --goal "stabilise throughput"
poetry run genesis benchmark run
poetry run genesis diag
```

## Monitoring & Alerting

1. **Metrics** – Prometheus scrapes `/metrics` on port `9000` using the namespace `genesis_*`. Dashboards include latency, throughput, reward deltas, and chaos recovery timelines.
2. **Tracing** – Enable OpenTelemetry by setting `GENESIS_OBSERVABILITY_ENABLE_TRACING=true`. Traces emit via OTLP/HTTP to the configured collector.
3. **Logs** – Structured JSON logs include `trace_id`, `job_id`, and `service` fields. Forward the stream to your SIEM or run `docker compose logs api` for quick inspection.
4. **Alerts** – Recommended alert rules:
   - API p95 latency > 120 ms for 5 minutes
   - Worker error ratio > 2% over 10 minutes
   - Chaos recovery duration > 12 seconds
   - Governance replay failures > 1 per hour

## Log & Metric Inspection Workflow

1. Use `poetry run genesis diag` for a live JSON summary.
2. Query Prometheus directly: `promql> rate(genesis_jobs_completed_total[5m])`.
3. Drill into Grafana dashboards shipped under `infra/grafana/` for correlated latency and reward visuals.
4. Pull JSON logs for a specific trace: `jq 'select(.trace_id=="<id>")' logs/genesis.json`.

## Troubleshooting

| Symptom | Likely Cause | Resolution |
|---------|--------------|------------|
| Redis connection errors in workers | Redis container stopped or credentials incorrect | Restart with `docker compose up -d redis` and verify `GENESIS_REDIS_URL`. |
| API returns 503 during deploy | Database migration pending or Postgres unavailable | Ensure Postgres is healthy, then rerun `make demo`; check `/health/ready` for details. |
| Workers stuck in "pending" | Worker concurrency too low or queue saturated | Increase `GENESIS_WORKER_CONCURRENCY`, inspect `poetry run genesis diag` for queue depth counters. |
| Governance actions rejected | Missing RBAC roles or signature invalid | Reload keys via environment variables and confirm policy file at `src/genesis/governance/policies.json`. |
| Temporal continuity alerts firing | Divergent branch merge or retrocausal replay mismatch | Execute `poetry run genesis merge --branch <id>` followed by `poetry run genesis continuity`. |

Maintain this playbook alongside incident retrospectives to ensure Genesis remains compliant and resilient in production environments.
