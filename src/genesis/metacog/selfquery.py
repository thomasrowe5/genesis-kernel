"""Self-query interface exposing reflexive state to internal agents."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from genesis.reflexion.twin import TwinState

from .reflection import ReflectionJournal
from .uncertainty import UncertaintyTracker


class SelfQueryService:
    """Provide read access to introspective state for internal actors."""

    def __init__(
        self,
        tracker: UncertaintyTracker,
        journal: ReflectionJournal,
    ) -> None:
        self._tracker = tracker
        self._journal = journal
        self._last_snapshot: TwinState | None = None

    def update_snapshot(self, snapshot: TwinState) -> None:
        self._last_snapshot = snapshot

    def metrics(self) -> Dict[str, Any]:
        return {
            "global_confidence": self._tracker.global_confidence(),
            "tracked_metrics": {
                record.key: {"mean": record.mean, "stddev": record.stddev, "at": record.last_updated.isoformat()}
                for record in self._tracker.export()
            },
        }

    def reflections(self, since: datetime | None = None) -> List[Dict[str, Any]]:
        entries = self._journal.query(since=since)
        return [
            {
                "reason": entry.reason,
                "prediction": entry.prediction,
                "result": entry.result,
                "delta": entry.delta,
                "confidence": entry.confidence,
                "created_at": entry.created_at.isoformat(),
            }
            for entry in entries
        ]

    def twin(self) -> TwinState | None:
        return self._last_snapshot
