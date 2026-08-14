"""Token Bucket rate limiter implementation."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class _Bucket:
    """Internal state for a single token bucket."""

    tokens: float
    last_refill: float
    capacity: float
    rate: float  # tokens per second

    def refill(self, now: float) -> None:
        """Refill tokens based on elapsed time."""
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill = now

    def try_acquire(self) -> bool:
        """Try to consume one token. Returns True if successful."""
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class TokenBucketRateLimiter:
    """Per-key token bucket rate limiter.

    Each unique key (e.g., target_url) gets its own bucket.
    Thread-safe via asyncio lock per bucket.
    """

    def __init__(self, rate: float, capacity: int) -> None:
        self._rate = rate
        self._capacity = capacity
        self._buckets: dict[str, _Bucket] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_bucket(self, key: str) -> _Bucket:
        """Get or create a bucket for the given key."""
        now = time.monotonic()
        if key not in self._buckets:
            self._buckets[key] = _Bucket(
                tokens=float(self._capacity),
                last_refill=now,
                capacity=float(self._capacity),
                rate=self._rate,
            )
            self._locks[key] = asyncio.Lock()
        return self._buckets[key]

    async def acquire(self, key: str) -> bool:
        """Try to acquire a token for the given key.

        Returns True if allowed, False if rate limited.
        """
        lock = self._locks.get(key)
        if lock is None:
            self._get_bucket(key)
            lock = self._locks[key]

        async with lock:
            bucket = self._get_bucket(key)
            now = time.monotonic()
            bucket.refill(now)
            allowed = bucket.try_acquire()

            if not allowed:
                logger.warning("rate_limited", key=key, tokens=bucket.tokens)

            return allowed

    def remove_bucket(self, key: str) -> None:
        """Remove a bucket (e.g., when target is no longer used)."""
        self._buckets.pop(key, None)
        self._locks.pop(key, None)
