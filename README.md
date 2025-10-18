# Genesis Kernel

Genesis Kernel is the first phase of a self-optimising AI infrastructure: a reliable kernel that
provides a durable job queue, API control plane, worker pool and first-class observability.

## Features

- **FastAPI control plane** exposing job and operational endpoints
- **Redis-backed queue** with idempotent enqueue support
- **PostgreSQL persistence** for jobs, events and worker heartbeats
- **Async worker** with graceful shutdown and structured logging
- **Prometheus metrics & Grafana dashboard** for insight into throughput and latency
- **Typer CLI** to interact with the service from the terminal
- **Docker Compose stack** for a reproducible local environment
- **Strict quality gates** via Ruff, mypy and pytest with coverage

## Quickstart

```bash
make setup
make up  # starts postgres, redis, api, worker, prometheus and grafana

# In another terminal once services are healthy
poetry run genesis enqueue --task fibonacci --n 25
```

Inspect job state via the API:

```bash
curl http://localhost:8000/jobs/<job_id>
```

To shut the stack down:

```bash
make down
```

## Development Workflow

- `make lint` – Ruff lint + format check
- `make typecheck` – mypy strict mode
- `make test` – pytest with coverage
- `make logs` – follow docker compose logs
- `make loadtest` – run the provided k6 script against the API

The project uses Poetry for dependency management. All commands run inside a fully reproducible
virtual environment (`poetry.lock` checked in).

## Repository Layout

```
src/genesis/        # application code
  api/              # FastAPI app and routers
  workers/          # worker runtime and executors
  queues/           # queue abstractions (Redis + in-memory for tests)
  cli/              # Typer-based CLI
  ...
docs/               # architecture and operations documentation
infra/              # Prometheus and Grafana configuration
scripts/            # helper scripts for local environments
rust/               # placeholder PyO3 module (future work)
```

## Phase 2 Preview

Phase 2 will introduce smarter routing, cache-aware scheduling and adaptive retry logic.
See `docs/architecture.md` for a system overview and `docs/operations.md` for the runbook.

