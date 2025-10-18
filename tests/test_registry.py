from __future__ import annotations

from genesis.registry.manager import ModuleRegistryManager


def setup_registry() -> ModuleRegistryManager:
    try:
        from sqlmodel import Session, create_engine  # type: ignore

        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        ModuleRegistryManager.create_all(engine)
        session = Session(engine)
        return ModuleRegistryManager(session)
    except Exception:
        return ModuleRegistryManager()


def test_register_and_leaderboard():
    registry = setup_registry()
    mv = registry.register_version("fibonacci", "v1", "src/genesis/modules/fibonacci.py")
    updated = registry.record_metrics(mv, 0.8, {"accuracy": 0.9, "latency": 0.1, "stability": 0.9})
    registry.activate_version(updated)
    board = registry.leaderboard()
    assert board[0]["name"] == "fibonacci"
    assert board[0]["active"] is True
    if registry.session:
        registry.session.close()


def test_replacement_event():
    registry = setup_registry()
    base = registry.register_version("sleep", "v1", "src/genesis/modules/sleep.py")
    registry.record_metrics(base, 0.5, {"accuracy": 0.7, "latency": 0.5, "stability": 0.8})
    registry.activate_version(base)

    challenger = registry.register_version("sleep", "v2", "src/genesis/modules/sleep_v2.py")
    registry.record_metrics(challenger, 0.8, {"accuracy": 0.9, "latency": 0.3, "stability": 0.95})
    event = registry.record_replacement(challenger, previous_version=base)
    assert event.payload["new_version"] == "v2"
    if registry.session:
        registry.session.close()
