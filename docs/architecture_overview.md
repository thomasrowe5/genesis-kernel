# Genesis Architecture Overview

This document summarises the consolidated Phase 1–12 architecture and explains how the
monorepo is structured. Each subsystem is packaged under the `src/genesis/` namespace with
clear hand-offs enforced through the unified API gateway.

```
+---------------------+        +---------------------+        +---------------------+
|  Genesis CLI / API  |<-----> |  Orchestration Bus   |<-----> |   Worker Executors   |
+---------------------+        +---------------------+        +---------------------+
         ^                               ^                               ^
         |                               |                               |
         |                               |                               |
         v                               v                               v
  Governance & Safety          Evaluator → Optimizer             Cognition & Reflexion
         ^                               |                               |
         |                               v                               v
         +------------------> Temporal / Retrocausal <-------------------+
```

* **Core** contains shared configuration, logging, observability, and persistence helpers.
* **Evaluator**, **Optimizer**, and **Router** modules orchestrate candidate testing and deployment.
* **Cognition** and **Reflexion** encapsulate autonomous reasoning loops and self-modeling.
* **Temporal** and **Retrocausal** maintain counterfactual histories and branching timelines.
* **Governance** codifies the Prime Ethic, RBAC, auditing, and release sign-off.
* **Infra** packages docker-compose, Kubernetes manifests, and observability dashboards.

Together these pieces deliver a reproducible platform that can be deployed locally or to
cloud environments. The unified API (`src/genesis/api/main.py`) exposes scoped routes with
versioned documentation and built-in RBAC enforcement.
