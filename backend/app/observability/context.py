"""Request-scoped context propagated via contextvars.

Anything logged inside a request handler automatically inherits the
``request_id`` and ``session_id`` bound here, so we never have to thread
them through call signatures.
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Final

_REQUEST_ID: Final[ContextVar[str]] = ContextVar("request_id", default="-")
_SESSION_ID: Final[ContextVar[str]] = ContextVar("session_id", default="-")


def set_request_id(value: str) -> None:
    _REQUEST_ID.set(value)


def get_request_id() -> str:
    return _REQUEST_ID.get()


def set_session_id(value: str) -> None:
    _SESSION_ID.set(value)


def get_session_id() -> str:
    return _SESSION_ID.get()


def snapshot() -> dict[str, str]:
    return {"request_id": _REQUEST_ID.get(), "session_id": _SESSION_ID.get()}
