# Replication and Resilience

The replication layer packages Genesis state, deploys it to remote regions, and
tracks lifecycle health for each replica.

```
BootstrapPackager --> tar.gz artifact --> ReplicaVerifier
                                          |
                                          v
                               ReplicaMigrator.deploy
                                          |
                                          v
                                 LifecycleCoordinator
```

1. **Bootstrap** – `BootstrapPackager` emits a tarball containing a manifest of
   configuration metadata. Each artifact is hashed and logged via the
   `genesis_replica_boots_total` counter.
2. **Verify** – `ReplicaVerifier` recomputes SHA-256 to guarantee integrity
   before allowing a replica to join the federation. Successful checks increase
   `genesis_self_repair_events_total` and update replica records.
3. **Deploy** – `ReplicaMigrator` persists replicas to the `Replica` table and
   marks them verified. The CLI `genesis replicate --target <region>` command ties
   all steps together for operator-free expansion.
4. **Lifecycle** – `LifecycleCoordinator` captures health signals and emits
   metrics whenever repair or retirement events are recorded, enabling Grafana
   dashboards to visualise the propagation of the self-repairing cloud.

Replica records include lineage (`origin_node`), hashes, and deployment
timestamps so that governance and observability layers can audit propagation
history across the civilization mesh.
