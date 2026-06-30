"""Bounded session store with TTL + LRU eviction.

The previous in-memory ``dict[str, SessionMemory]`` grew without bound — every
new ``session_id`` (including attacker-generated UUIDs) added a permanent
entry. This module replaces it with a fixed-capacity, time-windowed store
that is safe to use as the only session backend for a single-process
deployment. For multi-worker scale-out, swap the implementation for Redis
behind the same ``get/touch/purge`` surface.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class SessionStore(Generic[T]):
    def __init__(
        self,
        *,
        max_sessions: int = 5_000,
        ttl_seconds: int = 3_600,
        factory: Callable[[], T],
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max = max_sessions
        self._ttl = ttl_seconds
        self._factory = factory
        self._clock = clock
        self._data: "OrderedDict[str, tuple[float, T]]" = OrderedDict()
        self._lock = threading.RLock()

    def __len__(self) -> int:  # pragma: no cover - trivial
        with self._lock:
            return len(self._data)

    def get(self, key: str) -> T:
        with self._lock:
            self._evict_expired()
            entry = self._data.get(key)
            now = self._clock()
            if entry is None:
                value = self._factory()
                self._data[key] = (now, value)
            else:
                _, value = entry
                self._data[key] = (now, value)
                self._data.move_to_end(key)
            self._evict_overflow()
            return value

    def drop(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def _evict_expired(self) -> None:
        if self._ttl <= 0:
            return
        cutoff = self._clock() - self._ttl
        stale = [k for k, (ts, _) in self._data.items() if ts < cutoff]
        for k in stale:
            self._data.pop(k, None)

    def _evict_overflow(self) -> None:
        while len(self._data) > self._max:
            self._data.popitem(last=False)
