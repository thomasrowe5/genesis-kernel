# Genesis Architecture Overview (v1.0.1)

As of the Perfection Build every subsystem operates behind the unified FastAPI gateway, worker pool, and observability stack. The diagram below highlights how requests enter the kernel, traverse cognition, evaluation, optimisation, and governance loops, and feed metrics back into the command surface.

```
                             +-------------------------------+
                             |        Client Interfaces      |
                             |  (CLI, SDK, Automation Bus)   |
                             +---------------+---------------+
                                             |
                                             v
+-------------------+    +-------------------+    +-------------------+    +-------------------+
|  Unified FastAPI  |--> |  Cognition &      |--> | Evaluator &       |--> | Optimiser &       |
|  Gateway & RBAC   |    |  Experimentation  |    | Temporal Services |    | Orchestration Hub |
+---------+---------+    +---------+---------+    +---------+---------+    +---------+---------+
          |                       |                        |                        |
          |                       v                        v                        v
          |            +-------------------+    +-------------------+    +-------------------+
          |            | Reflexion &       |    | Governance &      |    | Cosmic / Cluster  |
          |            | Digital Twin Loop |    | Provenance Layer  |    | Federation Mesh   |
          |            +---------+---------+    +---------+---------+    +---------+---------+
          |                      \                 /         |                    /
          |                       \               /          |                   /
          v                        v             v           v                  v
+---------+---------+    +-------------------+    +-------------------+    +-------------------+
| Unified Metrics & |<---| Worker Executors  |<---| Retrocausal Store |<---| Persistence Tier  |
| Telemetry Fabric  |    | (Async Tasks, RL) |    | & Branch Manager  |    | (DB, Object, KV)  |
+-------------------+    +-------------------+    +-------------------+    +-------------------+
```

## End-to-End Flow

1. Operators and automated agents interact through the CLI or API gateway, authenticated via RBAC policies.
2. Cognition services expand goals into experiment plans and feed hypotheses to the evaluator.
3. Evaluator workers execute deterministic benchmarks, snapshot temporal branches, and stream metrics to the unified observability plane.
4. Optimiser and orchestration services promote high-performing modules, route traffic, and coordinate deployment rollouts.
5. Reflexion, governance, and provenance subsystems continuously audit outcomes, replay timelines, and enforce compliance before finalisation.
6. Metrics, traces, and artefacts persist into the shared telemetry store, enabling dashboards, alerting, and reproducible replay.

**Note:** As of v1.0.1 all subsystems run under a unified API, worker scheduler, and metrics stack, eliminating phase-specific integration glue.
