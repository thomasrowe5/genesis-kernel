# Multiverse Coherence

The multiverse layer tracks multiple concurrent Genesis branches and keeps them aligned through entropy-aware projection.

## Manifold Representation

```
+-----------------------------+
| Multiverse Manifold         |
|  - BranchState (metrics)    |
|  - Divergence matrix        |
+-----------------------------+
          |         |
          v         v
+-----------------------------+    +---------------------------+
| Coherence Engine            |    | Multiverse Observer       |
|  - PCA-style projection     |    |  - Divergence alerts      |
|  - Minimum energy merge     |    |  - Branch pruning         |
+-----------------------------+    +---------------------------+
```

* `manifold.py` stores the branch metrics and produces pairwise divergences.
* `coherence.py` averages across branches, generating entropy-minimised merges.
* `observer.py` monitors divergence thresholds and prunes unstable paths.

## Merge Flow

1. Extract all branches from the manifold.
2. Compute the shared metric basis and produce a mean projection.
3. Blend each branch toward the projection with configurable epsilon.
4. Emit the resulting coherence score and merged branch descriptor.

Prometheus gauges track both branch counts and coherence scores, allowing Grafana dashboards to visualise the overall multiverse health.
