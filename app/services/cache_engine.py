import time
from typing import Any, Dict, Optional
import threading

class SimpleTTLCache:
    """Thread-safe in-memory cache with Time-To-Live (TTL) expiration."""
    def __init__(self, default_ttl: int = 3600, max_items: int = 1000):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl
        self._max_items = max_items
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            item = self._cache[key]
            if time.time() > item["expires_at"]:
                del self._cache[key]
                return None
            return item["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            # Clean up if max_items reached
            if len(self._cache) >= self._max_items:
                now = time.time()
                # Remove expired items first
                expired_keys = [k for k, v in self._cache.items() if now > v["expires_at"]]
                for k in expired_keys:
                    del self._cache[k]
                # If still full, remove oldest 10%
                if len(self._cache) >= self._max_items:
                    sorted_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k]["expires_at"])
                    for k in sorted_keys[: max(1, self._max_items // 10)]:
                        del self._cache[k]

            expires_at = time.time() + (ttl if ttl is not None else self._default_ttl)
            self._cache[key] = {
                "value": value,
                "expires_at": expires_at
            }

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

# Global singleton cache instance
metadata_cache = SimpleTTLCache(default_ttl=3600, max_items=2000)
