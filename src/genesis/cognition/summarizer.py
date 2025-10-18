"""Automatic documentation generator for experiment results."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from genesis.research import ExperimentPlan, ExperimentResult


@dataclass(slots=True)
class ReportSummary:
    """Rendered summary document."""

    content: str
    created_at: datetime


class ReportSummarizer:
    """Produce Markdown summaries for experiment runs."""

    def render(self, plan: ExperimentPlan, result: ExperimentResult, insights: Iterable[str]) -> ReportSummary:
        timestamp = datetime.utcnow()
        lines = [
            "# Autonomous Research Report",
            "",
            f"Generated: {timestamp.isoformat()}Z",
            "",
            f"Goal: {plan.goal}",
            f"Hypothesis: {plan.hypothesis}",
            "",
            "## Controls",
        ]
        if plan.controls:
            for key, value in plan.controls.items():
                lines.append(f"- {key}: {value}")
        else:
            lines.append("- _None_")
        lines.extend([
            "",
            "## Metrics",
        ])
        if result.metrics:
            for metric, value in result.metrics.items():
                lines.append(f"- {metric}: {value:.3f}")
        else:
            lines.append("- _Unavailable_")
        lines.extend([
            "",
            "## Insights",
        ])
        insight_list = list(insights)
        if insight_list:
            for insight in insight_list:
                lines.append(f"- {insight}")
        else:
            lines.append("- _No insights_")
        lines.extend([
            "",
            "```mermaid",
            "graph LR",
            "  A[Plan] --> B[Experiment]",
            "  B --> C[Insight]",
            "  C --> D[Report]",
            "```",
        ])
        content = "\n".join(lines)
        return ReportSummary(content=content, created_at=timestamp)


__all__ = ["ReportSummarizer", "ReportSummary"]
