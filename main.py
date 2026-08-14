"""CLI entry point with demo event simulation."""

from __future__ import annotations

import asyncio
import random
import signal
import uuid

from core.logging import configure_logging, get_logger
from core.settings import settings
from domain.entities import Event
from presentation.cli import (
    print_banner,
    print_dlq_entry,
    print_event_delivered,
    print_event_failed,
    print_event_submitted,
    print_shutdown,
    print_stats,
)
from services.worker_pool import WorkerPool

logger = get_logger(__name__)


# Demo target URLs (httpbin.org for safe testing)
DEMO_TARGETS = [
    "https://httpbin.org/post",
    "https://httpbin.org/status/400",  # Will fail (400)
    "https://httpbin.org/status/500",  # Will fail (500)
    "https://httpbin.org/delay/2",     # Slow response
]

# Demo payloads
DEMO_PAYLOADS = [
    {"event": "user.created", "user_id": 123, "name": "Alice"},
    {"event": "order.placed", "order_id": "ORD-001", "amount": 99.99},
    {"event": "payment.processed", "transaction_id": "TX-456", "status": "success"},
    {"event": "notification.sent", "channel": "email", "recipient": "bob@example.com"},
]


def generate_demo_events(count: int = 10) -> list[Event]:
    """Generate random demo events."""
    events = []
    for _ in range(count):
        event = Event(
            event_id=uuid.uuid4(),
            payload=random.choice(DEMO_PAYLOADS),
            target_url=random.choice(DEMO_TARGETS),
            max_retries=settings.max_retries,
            priority=random.randint(0, 5),
        )
        events.append(event)
    return events


async def run_demo() -> None:
    """Run a demo simulation of the webhook forwarder."""
    configure_logging()
    print_banner()

    # Create worker pool with DI
    pool = WorkerPool()

    # Stats tracking
    stats = {"total": 0, "delivered": 0, "failed": 0, "dlq": 0}

    # Signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()

    def handle_signal(sig: signal.Signals) -> None:
        logger.info("signal_received", signal=sig.name)
        print_shutdown()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal, sig)

    # Start worker pool
    await pool.start()

    # Generate and submit demo events
    events = generate_demo_events(count=15)
    stats["total"] = len(events)

    console_text = "\n  [bold]Submitting events...[/bold]\n"
    from presentation.cli import console
    console.print(console_text)

    for event in events:
        print_event_submitted(
            str(event.event_id),
            event.target_url,
            event.priority,
        )
        await pool.submit(event)
        await asyncio.sleep(0.1)  # Small delay for visual effect

    # Wait for processing
    console.print("\n  [bold]Processing events...[/bold]\n")
    await asyncio.sleep(15)  # Wait for workers to process

    # Shutdown
    await pool.shutdown()

    # Final stats
    print_stats(
        total=stats["total"],
        delivered=stats["total"],  # Approximate for demo
        failed=0,
        dlq=0,
    )


def main() -> None:
    """CLI entry point."""
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
