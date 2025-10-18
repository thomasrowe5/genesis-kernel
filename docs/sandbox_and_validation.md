# Sandbox and Validation Loop

Every adaptation proposal is exercised in an isolated sandbox prior to rollout. The loop is orchestrated by `AdaptationPlanner`, `AdaptationSandbox`, and `ChangeValidator`:

```mermaid
sequenceDiagram
    participant Twin as Digital Twin
    participant Sandbox
    participant Simulator
    participant Introspector
    participant Validator
    participant Journal

    Twin->>Sandbox: Fork mirrored state
    Sandbox->>Simulator: Execute deterministic run
    Simulator->>Introspector: Predicted deltas
    Sandbox->>Introspector: Observed metrics
    Introspector->>Validator: Confidence & anomalies
    Validator->>Journal: Record rationale
    Validator-->>Twin: Approve or halt rollout
```

The planner records every decision in the reflection journal, including the change rationale, predicted deltas, final validation outcome, and associated confidence. CLI and API surfaces expose these artifacts so internal agents can understand causality and reproduce experiments before committing to production changes.
