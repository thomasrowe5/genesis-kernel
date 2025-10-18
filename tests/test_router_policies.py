from genesis.router.policies import PolicyCandidate, build_policy


def make_candidates() -> list[PolicyCandidate]:
    return [
        PolicyCandidate(
            module="fibonacci",
            version="v1",
            score=0.6,
            reward_ma=0.55,
            p95_ms=120.0,
            error_rate=0.1,
            traffic_share=0.6,
        ),
        PolicyCandidate(
            module="fibonacci",
            version="v2",
            score=0.9,
            reward_ma=0.8,
            p95_ms=110.0,
            error_rate=0.05,
            traffic_share=0.4,
        ),
    ]


def test_round_robin_policy_cycles():
    policy = build_policy("round_robin", rng_seed=1)
    candidates = make_candidates()
    order = [policy.select("fibonacci", candidates).version for _ in range(4)]
    assert order == ["v1", "v2", "v1", "v2"]


def test_ucb1_prefers_high_reward_after_updates():
    policy = build_policy("ucb1", rng_seed=2)
    candidates = make_candidates()
    policy.update("fibonacci", "v1", reward=0.2, success=True)
    policy.update("fibonacci", "v1", reward=0.2, success=True)
    policy.update("fibonacci", "v2", reward=0.9, success=True)
    choice = policy.select("fibonacci", candidates)
    assert choice.version == "v2"


def test_thompson_sampling_uses_seeded_rng():
    policy_a = build_policy("thompson", rng_seed=42)
    policy_b = build_policy("thompson", rng_seed=42)
    candidates = make_candidates()
    for _ in range(5):
        policy_a.update("fibonacci", "v2", reward=0.9, success=True)
        policy_b.update("fibonacci", "v2", reward=0.9, success=True)
    choice_a = policy_a.select("fibonacci", candidates)
    choice_b = policy_b.select("fibonacci", candidates)
    assert choice_a.version == choice_b.version


def test_epsilon_greedy_respects_best_candidate():
    policy = build_policy("epsilon_greedy", rng_seed=7, epsilon=0.0)
    candidates = make_candidates()
    choice = policy.select("fibonacci", candidates)
    assert choice.version == "v2"
