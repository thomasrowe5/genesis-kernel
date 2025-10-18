"""Logging configuration utilities."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    """A simple JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        payload: Dict[str, Any] = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key.startswith("_context_"):
                payload[key[9:]] = value
        return json.dumps(payload)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler])
