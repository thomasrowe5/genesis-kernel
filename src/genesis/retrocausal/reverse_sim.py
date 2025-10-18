"""Reverse-time simulation utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

from genesis.metrics import (
    genesis_retro_entropy_delta,
    genesis_retro_runs_total,
)


@dataclass(slots=True)
class TimelineCommit:
    """Lightweight representation of a recorded timeline commit."""

    commit_id: str
    reward: float
    entropy: float
    payload: Dict[str, float]


class TimelineRepository:
    """In-memory repository keeping ordered timeline commits."""

    def __init__(self, commits: Iterable[TimelineCommit] | None = None) -> None:
        self._commits: List[TimelineCommit] = list(commits or [])

    def add(self, commit: TimelineCommit) -> None:
        self._commits.append(commit)

    def ordered(self) -> Sequence[TimelineCommit]:
        return tuple(self._commits)

    def between(self, start: str, end: str) -> Sequence[TimelineCommit]:
        commits = {commit.commit_id: idx for idx, commit in enumerate(self._commits)}
        if start not in commits or end not in commits:
            raise KeyError(f"Unknown commit range {start}->{end}")
        start_idx = commits[start]
        end_idx = commits[end]
        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx
        return tuple(self._commits[start_idx : end_idx + 1])


@dataclass(slots=True)
class ReverseIntervention:
    """Represents a reversible delta applied during reverse simulation."""

    commit_id: str
    reward_adjustment: float
    entropy_adjustment: float
    rationale: str


@dataclass(slots=True)
class ReverseSimulationRequest:
    """Request payload describing a reverse run."""

    from_commit: str
    to_commit: str


@dataclass(slots=True)
class ReverseSimulationResult:
    """Result of a reverse simulation run."""

    path: Sequence[str]
    reward_delta: float
    entropy_delta: float
    interventions: Sequence[ReverseIntervention]


class ReverseSimulator:
    """Executes reverse simulations over stored timeline commits."""

    def __init__(self, timeline: TimelineRepository) -> None:
        self._timeline = timeline

    async def run(self, request: ReverseSimulationRequest) -> ReverseSimulationResult:
        commits = list(self._timeline.between(request.from_commit, request.to_commit))
        if not commits:
            raise ValueError("No commits found for simulation")
        forward = commits
        backward = list(reversed(forward))
        interventions: List[ReverseIntervention] = []
        latest_reward = forward[-1].reward
        target_entropy = forward[-1].entropy
        base_entropy = forward[0].entropy
        entropy_delta = target_entropy - base_entropy
        for commit in backward:
            reward_adjustment = latest_reward - commit.reward
            entropy_adjustment = target_entropy - commit.entropy
            interventions.append(
                ReverseIntervention(
                    commit_id=commit.commit_id,
                    reward_adjustment=reward_adjustment,
                    entropy_adjustment=entropy_adjustment,
                    rationale="retrocausal minimisation",
                )
            )
        reward_delta = latest_reward - forward[0].reward
        genesis_retro_runs_total.labels(status="success").inc()
        genesis_retro_entropy_delta.observe(entropy_delta)
        return ReverseSimulationResult(
            path=[commit.commit_id for commit in forward],
            reward_delta=reward_delta,
            entropy_delta=entropy_delta,
            interventions=list(reversed(interventions)),
        )


__all__ = [
    "TimelineCommit",
    "TimelineRepository",
    "ReverseIntervention",
    "ReverseSimulationRequest",
    "ReverseSimulationResult",
    "ReverseSimulator",
]
