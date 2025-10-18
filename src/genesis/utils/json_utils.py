"""JSON serialization helpers optimized for deterministic output."""
from __future__ import annotations

import json
from typing import Any, Callable, Optional

_ORJSON_OPTIONS = None

try:  # pragma: no cover - optional dependency import
    import orjson  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency import
    orjson = None  # type: ignore[assignment]
else:  # pragma: no cover - optional dependency import
    _ORJSON_OPTIONS = orjson.OPT_SORT_KEYS

DEFAULT_SEPARATORS = (",", ":")


def _serialize_with_stdlib(
    payload: Any,
    *,
    default: Optional[Callable[[Any], Any]] = None,
) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        default=default,
        separators=DEFAULT_SEPARATORS,
    )


def canonical_dumps(
    payload: Any,
    *,
    default: Optional[Callable[[Any], Any]] = None,
) -> str:
    """Serialize ``payload`` into a deterministic JSON string.

    The function prefers :mod:`orjson` for performance when available.  If the
    optional dependency cannot be imported we fall back to ``json.dumps`` with
    equivalent options to guarantee stable ordering and formatting.
    """

    if _ORJSON_OPTIONS is not None and orjson is not None:
        return orjson.dumps(  # type: ignore[no-untyped-call]
            payload,
            option=_ORJSON_OPTIONS,
            default=default,
        ).decode("utf-8")

    return _serialize_with_stdlib(payload, default=default)


def canonical_dumps_bytes(
    payload: Any,
    *,
    default: Optional[Callable[[Any], Any]] = None,
) -> bytes:
    """Serialize ``payload`` into deterministic JSON bytes."""

    if _ORJSON_OPTIONS is not None and orjson is not None:
        return orjson.dumps(  # type: ignore[no-untyped-call]
            payload,
            option=_ORJSON_OPTIONS,
            default=default,
        )

    return _serialize_with_stdlib(payload, default=default).encode("utf-8")


__all__ = ["canonical_dumps", "canonical_dumps_bytes"]
