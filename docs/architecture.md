# Genesis Kernel Architecture

```
CLI/API -> FastAPI Control Plane -> Redis Queue -> Worker Runner -> Task Executors
                                     |                     |
                                     v                     v
                                PostgreSQL <----- Metrics & Events
```

1. **Ingress** – Jobs are submitted through the FastAPI control plane or the Typer CLI.
2. **Queue** – The Redis broker stores serialized job payloads and guarantees FIFO semantics per
   priority lane.
3. **Persistence** – PostgreSQL records job metadata, state transitions and worker heartbeats.
4. **Workers** – Async worker processes fetch jobs, execute them and persist results.
5. **Observability** – Prometheus scrapes metrics from the API; Grafana dashboards visualise health.
6. **Resilience** – Worker heartbeats and exponential backoff provide durability in the face of
   transient faults.

For a deeper dive into the worker lifecycle and retry behaviour see the inline documentation in
`src/genesis/workers/runner.py`.
