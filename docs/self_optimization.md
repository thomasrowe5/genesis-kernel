# Genesis Kernel Self-Optimization

Phase 2 turns the Genesis kernel into a closed feedback loop composed of:

1. **Generation** – modules live under `src/genesis/modules/`.
2. **Evaluation** – the evaluator service reads declarative YAML cases from `benchmarks/` and runs AutoTest Cloud jobs.
3. **Optimization** – the optimizer loop computes a reward, records scores, and promotes new champions.
4. **Routing** – PromptMesh always forwards work to the highest scoring active variant.

## Reward Function

The optimizer normalises accuracy, latency, and stability to a \[0, 1] score using:

```
reward = clamp01(accuracy * stability * min(1.0, latency_baseline / latency))
```

The latency baseline defaults to one second and can be tuned per deployment. The reward is then passed through the Quant Systems `RewardEngine` stub for further shaping.

## Replacement Policy

1. Evaluate the candidate variant and persist raw metrics in the registry.
2. Compare the shaped reward to the active variant's score.
3. Promote the candidate if it beats the incumbent by at least `δ` (default 0.05).
4. Deactivate the previous champion and emit a `module_replacement` event.

Promotions update Prometheus metrics:

- `genesis_module_score{module,version}` – gauge with the latest reward.
- `genesis_replacements_total` – counter for replacements.

## Telemetry & Dashboards

Prometheus histograms expose evaluation durations via `genesis_eval_duration_seconds`. Grafana dashboards should track:

- Top five modules by score.
- Evaluation latency distribution.
- Replacement events over time.

## Future Work (Phase 3 Preview)

- Distributed evaluators scheduled via Kubernetes.
- On-policy reinforcement learning using the full Quant Systems stack.
- Persistent provenance graph stored in Neo4j.
- Multi-agent optimizers for population-based training.
