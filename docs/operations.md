# Operations Runbook

## Health Checks
- `/healthz` verifies the API is up.
- `/readyz` additionally probes PostgreSQL and Redis connectivity.

## Common Tasks
- **Restart worker**: `docker compose restart worker`
- **Inspect job**: `curl http://localhost:8000/jobs/<id>`
- **View metrics**: visit Prometheus at `http://localhost:9090` or Grafana at `http://localhost:3000`

## Alerts
- **Heartbeat missing**: alert if `genesis_worker_heartbeat` drops to zero for 2 scrape intervals.
- **Queue depth**: alert if `genesis_queue_depth` > 100 for 5m.
- **Failure rate**: alert if the ratio of failed to completed jobs exceeds 5% over 10m.

## Failure Handling
- **Database unavailable**: workers pause intake and retry with exponential backoff.
- **Redis unavailable**: API returns 503 on enqueue; operators should check Docker Compose health.
- **Poison job**: after max retries the job is marked as `dead-letter` and remains queryable.

## Next Steps (Phase 2)
- Introduce smart routing with awareness of task execution times.
- Add caching for idempotent HTTP fetch results.
- Provide UI for dead-letter queue inspection and requeue.
