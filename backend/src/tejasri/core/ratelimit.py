"""In-memory token-bucket rate limiter (per client key).

Suitable for a single-process deployment; the interface is small enough
that a Redis-backed implementation can replace it for horizontal scale
(documented in docs/SCALABILITY notes). Auth endpoints get a stricter
bucket than the general API to slow credential stuffing.
"""

import threading
import time


class TokenBucketLimiter:
    def __init__(self, capacity: int, refill_per_minute: int) -> None:
        self._capacity = float(capacity)
        self._refill_per_second = refill_per_minute / 60.0
        self._buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_ts)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            tokens, last = self._buckets.get(key, (self._capacity, now))
            tokens = min(self._capacity, tokens + (now - last) * self._refill_per_second)
            if tokens < 1.0:
                self._buckets[key] = (tokens, now)
                return False
            self._buckets[key] = (tokens - 1.0, now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()
