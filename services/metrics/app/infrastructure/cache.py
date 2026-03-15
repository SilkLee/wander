from __future__ import annotations

import time
import threading
from typing import Any


class TTLCache:
    """Simple in-memory cache with per-key TTL expiration.

    Thread-safe via a lock. Designed for caching DORA metric responses
    to avoid recalculating on every request.
    """

    def __init__(self, default_ttl: float = 30.0) -> None:
        self._store: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        """Return cached value if present and not expired, else None."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Store a value with optional custom TTL (seconds)."""
        ttl = ttl if ttl is not None else self._default_ttl
        with self._lock:
            self._store[key] = (value, time.monotonic() + ttl)

    def invalidate(self, key: str) -> None:
        """Remove a specific key from cache."""
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        """Remove all cached entries."""
        with self._lock:
            self._store.clear()


# Module-level singleton used by the DORA endpoint
dora_cache = TTLCache(default_ttl=30.0)
