# Genesis Cluster Architecture

## Overview

Genesis Phase 4 introduces a distributed control plane that coordinates multiple
optimizer and evaluator nodes. Each node exposes both HTTP and gRPC compatible
interfaces and communicates registry updates through a lightweight gossip
protocol built on top of `httpx`.

## Component Diagram

```
+------------+      gossip       +------------+      gossip       +------------+
| node-a     | <---------------> | node-b     | <---------------> | node-c     |
|            |                   |            |                   |            |
| FastAPI    |                   | FastAPI    |                   | FastAPI    |
| Scheduler  |                   | Scheduler  |                   | Scheduler  |
| Registry   |                   | Registry   |                   | Registry   |
+------------+                   +------------+                   +------------+
       ^                                ^                                ^
       |                                |                                |
       +--------- libcluster.rs --------+---------- libcluster.rs -------+
```

## Heartbeat and Sync Sequence

```
Node A                    Node B                     Node C
  |                          |                          |
  |--- heartbeat ----------->|                          |
  |                          |--- gossip module ------->|
  |<-- gossip metrics -------|                          |
  |                          |                          |
  |--- replay request --------------------------------->|
  |<-- replay digest -----------------------------------|
```

## Scheduler

Genesis uses a consistent hashing ring to route experiments and evaluation jobs
onto the node responsible for a given module version. Nodes advertise their
capacity as weights during gossip; the scheduler adjusts the ring without
interrupting in-flight workloads.

## Registry Synchronisation

The registry synchroniser batches ModuleVersion updates and pushes them to peer
nodes every heartbeat. Nodes apply deltas idempotently to maintain causal
consistency without requiring a leader for every write. Leader election is
reserved for quorum-level operations such as policy updates.

## Deployment

Add the cluster router to the FastAPI application:

```python
from genesis.api.routes.cluster import router as cluster_router
app.include_router(cluster_router)
```

To join the mesh from the CLI:

```bash
poetry run genesis cluster join --peer http://10.0.0.5:8080
```

The `genesis cluster status` command surfaces live heartbeat and health data,
mirroring the `/cluster/nodes` API response.
