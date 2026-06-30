"""Structured logging via stdlib ``logging`` with a JSON formatter.

We deliberately avoid pulling in ``structlog`` to keep the dependency
footprint small. The custom formatter merges the request-scoped context
(see ``context.py``) into every record, so a single ``logger.info(...)``
call from anywhere in the request path produces a line tagged with the
right ``request_id`` and ``session_id``.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any

from .context import snapshot

_CONFIGURED = False


class JsonFormatter(logging.Formatter):
    """Single-line JSON log records, suitable for any log aggregator."""

    # Attributes already covered by structured output — drop from `extra`.
    _RESERVED = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "message", "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
                  + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        payload.update(snapshot())
        for key, value in record.__dict__.items():
            if key in self._RESERVED or key.startswith("_"):
                continue
            try:
                json.dumps(value)
            except (TypeError, ValueError):
                value = repr(value)
            payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure(level: str = "INFO") -> None:
    """Idempotent global logging setup. Safe to call from lifespan + tests."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())
    # Wipe any default handlers (uvicorn installs its own; we replace them
    # for app loggers but leave uvicorn.access untouched).
    root.handlers = [handler]
    for noisy in ("uvicorn.error", "uvicorn"):
        logging.getLogger(noisy).handlers = [handler]
        logging.getLogger(noisy).propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
