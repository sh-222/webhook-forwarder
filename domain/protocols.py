"""Domain protocols (interfaces) for dependency inversion."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from domain.entities import DeadLetterEvent, Event


@runtime_checkable
class RateLimiterProtocol(Protocol):
    """Token bucket rate limiter interface."""

    async def acquire(self, key: str) -> bool:
        """Try to acquire a token for the given key. Returns True if allowed."""
        ...


@runtime_checkable
class HttpClientProtocol(Protocol):
    """HTTP client interface for sending webhooks."""

    async def post(self, url: str, payload: dict) -> tuple[int, str]:
        """Send POST request. Returns (status_code, body)."""
        ...

    async def close(self) -> None:
        """Close the client."""
        ...


@runtime_checkable
class DeadLetterStorageProtocol(Protocol):
    """DLQ storage interface."""

    async def append(self, entry: DeadLetterEvent) -> None:
        """Append a dead letter event to storage."""
        ...

    async def alert(self, entry: DeadLetterEvent) -> None:
        """Generate an alert for a dead letter event."""
        ...
