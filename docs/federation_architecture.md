# Federation Architecture

The civilization layer introduces a federated mesh responsible for coordinating
state between autonomous Genesis clusters. The overlay exposes secure
peer-registration, consensus voting, and state distribution while relying on
cryptographic identities to authenticate every message.

```
+-------------------+         +------------------+         +------------------+
|   Peer Registry   |<------->|  Consensus Pool  |<------->|  Economy Ledger  |
+-------------------+         +------------------+         +------------------+
          ^                            ^                             |
          |                            |                             v
          |                            |                   +-------------------+
          |                            |                   | Ethics & Tribunal |
          v                            v                   +-------------------+
+-------------------+         +------------------+                     |
| Identity Registry |-------->| Federation Mesh |<---------------------+
+-------------------+         +------------------+
```

The `FederationMesh` coordinates peer membership and orchestrates PBFT-style
rounds through the shared `ConsensusEngine`. Approved commits produce signed
snapshots via the in-memory identity registry so that downstream services can
validate governance changes out of band.

Prometheus counters track active peers, consensus rounds, and ledger
transactions enabling Grafana dashboards to visualise quorum stability and
resource flow across the mesh.
