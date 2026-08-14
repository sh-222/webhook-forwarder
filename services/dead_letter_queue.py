"""Dead Letter Queue: JSON Lines storage + alerting."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from core.logging import get_logger
from core.settings import settings
from domain.entities import DeadLetterEvent, Event

logger = get_logger(__name__)


class DeadLetterQueue:
    """Stores failed events in JSON Lines format and generates alerts."""

    def __init__(self, file_path: str | None = None) -> None:
        self._file_path = Path(file_path or settings.dlq_file)

    async def append(self, entry: DeadLetterEvent) -> None:
        """Append a dead letter event to the JSONL file."""
        record = {
            "event_id": str(entry.event.event_id),
            "target_url": entry.event.target_url,
            "payload": entry.event.payload,
            "retry_count": entry.event.retry_count,
            "max_retries": entry.event.max_retries,
            "priority": entry.event.priority,
            "error_message": entry.error_message,
            "last_status_code": entry.last_status_code,
            "failed_at": entry.failed_at.isoformat(),
        }

        line = json.dumps(record, ensure_ascii=False) + "\n"

        # Append to file (async-friendly for small writes)
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.open("a", encoding="utf-8").write(line)

        logger.info(
            "dlq_appended",
            event_id=str(entry.event.event_id),
            target_url=entry.event.target_url,
            file=str(self._file_path),
        )

    async def alert(self, entry: DeadLetterEvent) -> None:
        """Generate an alert for a dead letter event.

        In production this would integrate with PagerDuty/Slack/etc.
        Currently logs a structured alert.
        """
        logger.critical(
            "DLQ_ALERT",
            event_id=str(entry.event.event_id),
            target_url=entry.event.target_url,
            error=entry.error_message,
            retry_count=entry.event.retry_count,
            max_retries=entry.event.max_retries,
            last_status=entry.last_status_code,
            failed_at=entry.failed_at.isoformat(),
        )

    @staticmethod
    def create_dlq_event(
        event: Event,
        error_message: str,
        last_status_code: int | None = None,
    ) -> DeadLetterEvent:
        """Factory for creating DeadLetterEvent from a failed Event."""
        return DeadLetterEvent(
            event=event,
            error_message=error_message,
            last_status_code=last_status_code,
            failed_at=datetime.now(timezone.utc),
        )
