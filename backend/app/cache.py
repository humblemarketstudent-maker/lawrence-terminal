"""Process-local TTL cache with stale reads for graceful degradation."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheHit:
    value: Any
    fresh: bool
    stored_at: float


class TTLCache:
    def __init__(self) -> None:
        self._data: dict[str, tuple[float, float, Any]] = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: Any, ttl: float) -> None:
        now = time.time()
        with self._lock:
            self._data[key] = (now + ttl, now, value)

    def get(self, key: str, allow_stale: bool = False) -> CacheHit | None:
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            expires, stored, value = item
            fresh = time.time() < expires
            if fresh or allow_stale:
                return CacheHit(value=value, fresh=fresh, stored_at=stored)
            return None

    def invalidate(self, prefix: str | None = None) -> None:
        with self._lock:
            if prefix is None:
                self._data.clear()
                return
            for key in [key for key in self._data if key.startswith(prefix)]:
                self._data.pop(key, None)

    def stats(self) -> dict[str, int]:
        now = time.time()
        with self._lock:
            fresh = sum(1 for expires, _, _ in self._data.values() if expires > now)
            return {"entries": len(self._data), "fresh": fresh}
