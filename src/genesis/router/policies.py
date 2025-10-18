"""Bandit policies used by the PromptRouter."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Tuple


@dataclass(frozen=True)
class PolicyCandidate:
    """Snapshot of a module variant presented to the policy."""

    module: str
    version: str
    score: float
    reward_ma: float
    p95_ms: float
    error_rate: float
    traffic_share: float


class BasePolicy:
    """Base class providing bookkeeping helpers for policies."""

    def __init__(self, *, rng: Optional[random.Random] = None) -> None:
        self._rng = rng or random.Random(0)

    def update(self, module: str, version: str, reward: float, *, success: bool) -> None:
        """Update the internal state based on an observed outcome."""

    def select(self, module: str, candidates: Iterable[PolicyCandidate]) -> PolicyCandidate:
        raise NotImplementedError


class RoundRobinPolicy(BasePolicy):
    """Cycles through candidates sequentially per module."""

    def __init__(self, *, rng: Optional[random.Random] = None) -> None:
        super().__init__(rng=rng)
        self._indices: Dict[str, int] = {}

    def select(self, module: str, candidates: Iterable[PolicyCandidate]) -> PolicyCandidate:
        pool: List[PolicyCandidate] = list(candidates)
        if not pool:
            raise ValueError("No candidates available for routing")
        idx = self._indices.get(module, 0)
        choice = pool[idx % len(pool)]
        self._indices[module] = (idx + 1) % len(pool)
        return choice


class EpsilonGreedyPolicy(BasePolicy):
    """Selects the best candidate with probability 1-epsilon, otherwise explores."""

    def __init__(self, epsilon: float = 0.1, *, rng: Optional[random.Random] = None) -> None:
        super().__init__(rng=rng)
        self._epsilon = epsilon

    def select(self, module: str, candidates: Iterable[PolicyCandidate]) -> PolicyCandidate:
        pool = list(candidates)
        if not pool:
            raise ValueError("No candidates available for routing")
        if self._rng.random() < self._epsilon:
            return self._rng.choice(pool)
        return max(pool, key=lambda c: (c.reward_ma, c.score))


class UCB1Policy(BasePolicy):
    """Upper confidence bound policy balancing exploration and exploitation."""

    def __init__(self, *, rng: Optional[random.Random] = None) -> None:
        super().__init__(rng=rng)
        self._counts: Dict[Tuple[str, str], int] = {}
        self._total: Dict[str, int] = {}
        self._rewards: Dict[Tuple[str, str], float] = {}

    def update(self, module: str, version: str, reward: float, *, success: bool) -> None:
        key = (module, version)
        self._counts[key] = self._counts.get(key, 0) + 1
        self._total[module] = self._total.get(module, 0) + 1
        self._rewards[key] = self._rewards.get(key, 0.0) + reward

    def select(self, module: str, candidates: Iterable[PolicyCandidate]) -> PolicyCandidate:
        pool = list(candidates)
        if not pool:
            raise ValueError("No candidates available for routing")
        module_total = max(self._total.get(module, 1), 1)
        scores = []
        for candidate in pool:
            key = (candidate.module, candidate.version)
            count = self._counts.get(key, 0)
            if count == 0:
                bonus = float("inf")
                mean = 0.0
            else:
                mean = self._rewards.get(key, 0.0) / count
                bonus = math.sqrt(2.0 * math.log(module_total + 1) / count)
            scores.append((mean + bonus, candidate))
        scores.sort(key=lambda item: item[0], reverse=True)
        return scores[0][1]


class ThompsonSamplingPolicy(BasePolicy):
    """Thompson sampling with Beta priors over binary success events."""

    def __init__(self, *, rng: Optional[random.Random] = None) -> None:
        super().__init__(rng=rng)
        self._alphas: Dict[Tuple[str, str], float] = {}
        self._betas: Dict[Tuple[str, str], float] = {}

    def update(self, module: str, version: str, reward: float, *, success: bool) -> None:
        key = (module, version)
        alpha = self._alphas.get(key, 1.0)
        beta = self._betas.get(key, 1.0)
        if success:
            alpha += reward
        else:
            beta += max(0.0, 1.0 - reward)
        self._alphas[key] = alpha
        self._betas[key] = beta

    def select(self, module: str, candidates: Iterable[PolicyCandidate]) -> PolicyCandidate:
        pool = list(candidates)
        if not pool:
            raise ValueError("No candidates available for routing")
        best_score = -1.0
        best_candidate = pool[0]
        for candidate in pool:
            key = (candidate.module, candidate.version)
            alpha = self._alphas.get(key, 1.0)
            beta = self._betas.get(key, 1.0)
            sample = self._rng.betavariate(alpha, beta)
            if sample > best_score:
                best_score = sample
                best_candidate = candidate
        return best_candidate


POLICY_REGISTRY: Mapping[str, type[BasePolicy]] = {
    "round_robin": RoundRobinPolicy,
    "epsilon_greedy": EpsilonGreedyPolicy,
    "ucb1": UCB1Policy,
    "thompson": ThompsonSamplingPolicy,
}


def build_policy(name: str, *, rng_seed: int = 0, **kwargs: object) -> BasePolicy:
    """Factory returning a configured policy instance."""

    key = name.lower()
    try:
        policy_cls = POLICY_REGISTRY[key]
    except KeyError as exc:  # pragma: no cover - defensive branch
        raise ValueError(f"Unknown routing policy: {name}") from exc
    rng = random.Random(rng_seed)
    return policy_cls(rng=rng, **kwargs)


__all__ = [
    "PolicyCandidate",
    "BasePolicy",
    "RoundRobinPolicy",
    "EpsilonGreedyPolicy",
    "UCB1Policy",
    "ThompsonSamplingPolicy",
    "build_policy",
]
