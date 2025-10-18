# Evolution and Speciation

Interstellar growth encourages localized experimentation while preserving
compatibility. The `genesis.evolution` namespace introduces three cooperating
layers:

1. `MutationOperator` adds controlled Gaussian perturbations bounded by
   configurable deltas.
2. `SpeciationEngine` spins new branches with tracked mutation vectors and
   divergence scores.
3. `ConvergenceEngine` reconciles branches via fitness- and ethics-weighted
   averaging.
4. `HeritageCodex` preserves the immutable Prime Ethic signature used by Seeds
   and branch mergers alike.

```mermaid
graph LR
    HeritageCodex --> SeedBuilder
    SeedBuilder --> SpeciationEngine
    SpeciationEngine -->|branches| ConvergenceEngine
    ConvergenceEngine -->|merged genome| CosmicNetworkService
```

During autonomy cycles, the Speciation engine emits parameter sets with mutation
vectors smaller than `δ`. When convergence is triggered, each branch contributes
according to `(fitness + ethics_bonus)` ensuring ethical drift remains bounded.
