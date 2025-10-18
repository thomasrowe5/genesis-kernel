"""Publication helpers for cognitive research artifacts."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from .experiment import ExperimentPlan, ExperimentResult


@dataclass(slots=True)
class PublicationArtifact:
    """Serializable representation of a research report."""

    plan: ExperimentPlan
    result: ExperimentResult
    insights: Iterable[str]

    def to_markdown(self) -> str:
        """Render the artifact as Markdown."""

        duration = self.result.finished_at - self.result.started_at
        metrics_lines = "\n".join(
            f"- **{metric}**: {value:.3f}" for metric, value in self.result.metrics.items()
        )
        insight_lines = "\n".join(f"- {insight}" for insight in self.insights) or "- _No insights recorded_"
        return (
            f"# Experiment Report\\n\\n"
            f"**Plan ID:** {self.plan.id}\\n\\n"
            f"**Goal:** {self.plan.goal}\\n\\n"
            f"**Hypothesis:** {self.plan.hypothesis}\\n\\n"
            f"**Controls:** {self._format_mapping(self.plan.controls)}\\n\\n"
            f"**Duration:** {duration:.2f}s\\n\\n"
            f"## Metrics\\n{metrics_lines}\\n\\n"
            f"## Insights\\n{insight_lines}\\n\\n"
            "```mermaid\\ngraph TD\\n  plan[Plan Generated] --> run[Experiment Run]\\n  run --> report[Report Published]\\n```\\n"
        )

    @staticmethod
    def _format_mapping(mapping: Mapping[str, object]) -> str:
        if not mapping:
            return "{}"
        items = ", ".join(f"{key}={value}" for key, value in mapping.items())
        return "{" + items + "}"

    def write(self, destination: Path) -> None:
        destination.write_text(self.to_markdown(), encoding="utf-8")


__all__ = ["PublicationArtifact"]
