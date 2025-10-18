from __future__ import annotations

import json
from datetime import datetime, timezone

from genesis.utils.json_utils import canonical_dumps, canonical_dumps_bytes


def test_canonical_dumps_is_deterministic() -> None:
    payload = {"b": 1, "a": 2}
    first = canonical_dumps(payload)
    second = canonical_dumps(payload)
    assert first == second
    assert first.index('"a"') < first.index('"b"')
    assert json.loads(first) == {"a": 2, "b": 1}


def test_canonical_dumps_bytes_respects_default() -> None:
    payload = {"when": datetime(2024, 1, 1, tzinfo=timezone.utc)}
    dumped = canonical_dumps(payload, default=str)
    dumped_bytes = canonical_dumps_bytes(payload, default=str)
    assert dumped_bytes == dumped.encode("utf-8")
    assert json.loads(dumped)["when"].startswith("2024-01-01")
