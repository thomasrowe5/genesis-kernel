# Genesis Operations Manual

This manual describes how to deploy, monitor, and troubleshoot the unified Genesis platform.

## Prerequisites
- Python 3.11
- Docker + Docker Compose (for local deployments)
- Optional: kubectl & Helm (for cloud deployments)
- Redis, Postgres, Prometheus, Grafana images available locally or from a registry

## Configuration
All runtime settings are managed via `GenesisSettings` (`src/genesis/core/config.py`). Override
values by exporting environment variables with the `GENESIS_` prefix.

```
GENESIS_ENVIRONMENT=staging
GENESIS_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/genesis
GENESIS_REDIS_URL=redis://localhost:6379/0
GENESIS_LOGGING_LEVEL=DEBUG
```

## Deployments

### Local (docker-compose)

```bash
poetry run genesis deploy local --apply
```

This command uses `infra/docker-compose.yaml` to start Postgres, Redis, Prometheus, Grafana,
the API gateway, and a background worker. Health checks on `/health/live` and `/health/ready`
confirm readiness.

### Cloud (Kubernetes)

```bash
poetry run genesis deploy cloud --apply
```

Applies the manifests found in `infra/k8s/`. Ensure secrets (API keys, database credentials)
are provisioned via Kubernetes secrets before deploying.

## Observability
- Prometheus scrapes metrics from the API gateway on port `9000`.
- Grafana dashboards are provisioned via `infra/grafana/dashboard.json`.
- Structured JSON logs include `trace_id`, `job_id`, and HTTP metadata for correlation.
- Capture a point-in-time snapshot by running `poetry run genesis diag --output diagnostics.json`.

## Benchmarks

Run the benchmark suite to generate throughput, latency, and reward delta reports:

```bash
poetry run genesis benchmark run
```

Results are stored in the `benchmarks/` directory by default and exported as JSON.

## Troubleshooting
- Verify environment variables using `poetry run genesis config show` (future enhancement).
- Inspect Docker container logs for failing services.
- Ensure RBAC keys are loaded – missing credentials cause `401` responses on health endpoints.
- Use `poetry run genesis docs build` to regenerate docs and verify configuration hints.
- Run `poetry run genesis diag` to confirm critical metrics such as `genesis_uptime_seconds` and `genesis_retry_total`.
