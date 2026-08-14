"""Domain entities: Event DTO, DeadLetterEvent."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class Event:
    """Incoming webhook event to be forwarded."""

    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    payload: dict[str, Any] = field(default_factory=dict)
    target_url: str = ""
    retry_count: int = 0
    max_retries: int = 3
    priority: int = 0  # Higher = more urgent

    def with_retry(self) -> Event:
        """Return a new Event with incremented retry_count."""
        return Event(
            event_id=self.event_id,
            payload=self.payload,
            target_url=self.target_url,
            retry_count=self.retry_count + 1,
            max_retries=self.max_retries,
            priority=self.priority,
        )

    def __lt__(self, other: Event) -> bool:
        """For priority queue: higher priority number = dequeued first."""
        return self.priority > other.priority


@dataclass(frozen=True, slots=True)
class DeadLetterEvent:
    """Event that exhausted all retries — stored in DLQ."""

    event: Event
    error_message: str
    last_status_code: int | None
    failed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
