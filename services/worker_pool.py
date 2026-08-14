"""Async worker pool with priority queue."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field

from core.exceptions import QueueFullError, WebhookDeliveryError
from core.logging import get_logger
from core.settings import settings
from domain.entities import DeadLetterEvent, Event
from domain.protocols import DeadLetterStorageProtocol, HttpClientProtocol, RateLimiterProtocol
from services.dead_letter_queue import DeadLetterQueue
from services.webhook_sender import WebhookSender

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class _PriorityEvent:
    """Wrapper for priority queue ordering (negate priority for max-heap)."""

    priority: int
    sequence: int
    event: Event

    def __lt__(self, other: _PriorityEvent) -> bool:
        """Higher priority first; tie-break by sequence (FIFO)."""
        if self.priority != other.priority:
            return self.priority > other.priority
        return self.sequence < other.sequence


class WorkerPool:
    """Async worker pool that processes events from a priority queue."""

    def __init__(
        self,
        worker_count: int | None = None,
        queue_max_size: int | None = None,
        http_client: HttpClientProtocol | None = None,
        rate_limiter: RateLimiterProtocol | None = None,
        dlq: DeadLetterStorageProtocol | None = None,
    ) -> None:
        self._worker_count = worker_count or settings.worker_count
        self._queue_max_size = queue_max_size or settings.queue_max_size

        # DI: inject or create defaults
        from adapters.http_client import HttpClient

        self._http_client = http_client or HttpClient()
        self._rate_limiter = rate_limiter or __import__(
            "services.rate_limiter", fromlist=["TokenBucketRateLimiter"]
        ).TokenBucketRateLimiter(
            rate=settings.rate_limit_rate,
            capacity=settings.rate_limit_capacity,
        )
        self._dlq = dlq or DeadLetterQueue()

        self._sender = WebhookSender(self._http_client, self._rate_limiter)

        self._queue: asyncio.PriorityQueue[_PriorityEvent] = asyncio.PriorityQueue(
            maxsize=self._queue_max_size
        )
        self._workers: list[asyncio.Task[None]] = []
        self._shutdown_event = asyncio.Event()
        self._sequence = 0
        self._active_tasks: set[asyncio.Task[None]] = set()

    @property
    def queue_size(self) -> int:
        """Current number of events in the queue."""
        return self._queue.qsize()

    @property
    def is_running(self) -> bool:
        """Whether the pool is still running."""
        return not self._shutdown_event.is_set()

    async def submit(self, event: Event) -> None:
        """Submit an event to the priority queue.

        Raises:
            QueueFullError: If the queue is at capacity.
        """
        if self._shutdown_event.is_set():
            logger.warning("submit_after_shutdown", event_id=str(event.event_id))
            return

        self._sequence += 1
        wrapped = _PriorityEvent(
            priority=event.priority,
            sequence=self._sequence,
            event=event,
        )

        try:
            self._queue.put_nowait(wrapped)
            logger.info(
                "event_queued",
                event_id=str(event.event_id),
                target_url=event.target_url,
                priority=event.priority,
                queue_size=self._queue.qsize(),
            )
        except asyncio.QueueFull:
            raise QueueFullError(self._queue_max_size)

    async def start(self) -> None:
        """Start the worker pool."""
        logger.info("worker_pool_starting", worker_count=self._worker_count)

        for i in range(self._worker_count):
            task = asyncio.create_task(self._worker_loop(worker_id=i))
            self._workers.append(task)

        logger.info("worker_pool_started", worker_count=self._worker_count)

    async def shutdown(self) -> None:
        """Gracefully shut down the worker pool."""
        logger.info("worker_pool_shutting_down")
        self._shutdown_event.set()

        # Wait for active tasks to complete
        if self._active_tasks:
            logger.info(
                "waiting_for_active_tasks", count=len(self._active_tasks)
            )
            await asyncio.wait(
                self._active_tasks,
                timeout=settings.shutdown_timeout,
            )

        # Cancel workers
        for worker in self._workers:
            worker.cancel()

        # Wait for workers to finish
        await asyncio.gather(*self._workers, return_exceptions=True)

        await self._http_client.close()

        logger.info("worker_pool_shutdown_complete")

    async def _worker_loop(self, worker_id: int) -> None:
        """Main loop for a single worker."""
        logger.info("worker_started", worker_id=worker_id)

        while not self._shutdown_event.is_set():
            try:
                # Wait for event with timeout to check shutdown
                try:
                    wrapped = await asyncio.wait_for(
                        self._queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Process event
                task = asyncio.create_task(
                    self._process_event(wrapped.event, worker_id)
                )
                self._active_tasks.add(task)
                task.add_done_callback(self._active_tasks.discard)

            except asyncio.CancelledError:
                break

        logger.info("worker_stopped", worker_id=worker_id)

    async def _process_event(self, event: Event, worker_id: int) -> None:
        """Process a single event with retry logic."""
        logger.info(
            "processing_event",
            event_id=str(event.event_id),
            worker_id=worker_id,
            retry_count=event.retry_count,
        )

        try:
            await self._sender.send(event)

        except WebhookDeliveryError as exc:
            logger.warning(
                "event_delivery_failed",
                event_id=str(event.event_id),
                retry_count=event.retry_count,
                error=str(exc),
            )

            if event.retry_count >= event.max_retries:
                # Move to DLQ
                dlq_entry = DeadLetterQueue.create_dlq_event(
                    event=event,
                    error_message=str(exc),
                    last_status_code=exc.status_code,
                )
                await self._dlq.append(dlq_entry)
                await self._dlq.alert(dlq_entry)
            else:
                # Re-enqueue with incremented retry count
                retried_event = event.with_retry()
                await self.submit(retried_event)

        except Exception as exc:
            logger.error(
                "unexpected_event_error",
                event_id=str(event.event_id),
                error=str(exc),
            )
            # Move to DLQ on unexpected errors
            dlq_entry = DeadLetterQueue.create_dlq_event(
                event=event,
                error_message=str(exc),
            )
            await self._dlq.append(dlq_entry)
            await self._dlq.alert(dlq_entry)
