# Genesis Kernel Demo

1. Start the stack:
   ```bash
   make up
   ```
2. Enqueue a Fibonacci job:
   ```bash
   poetry run genesis enqueue --task fibonacci --n 32
   ```
   Note the returned `job_id`.
3. Poll the API until the job succeeds:
   ```bash
   curl http://localhost:8000/jobs/<job_id>
   ```
4. Observe metrics:
   - Prometheus: http://localhost:9090
   - Grafana dashboard: http://localhost:3000
5. Demonstrate graceful shutdown:
   ```bash
   docker compose stop worker
   ```
   The worker logs include a message indicating a graceful drain and heartbeat cessation.
