"""Base exception hierarchy for the application."""

from __future__ import annotations


class AppError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str = "", *, code: str = "UNKNOWN") -> None:
        self.code = code
        super().__init__(message)


class RateLimitExceededError(AppError):
    """Raised when rate limit for a target URL is exceeded."""

    def __init__(self, target_url: str) -> None:
        self.target_url = target_url
        super().__init__(
            f"Rate limit exceeded for {target_url}",
            code="RATE_LIMIT_EXCEEDED",
        )


class WebhookDeliveryError(AppError):
    """Raised when webhook delivery fails after all retries."""

    def __init__(self, target_url: str, status_code: int | None = None) -> None:
        self.target_url = target_url
        self.status_code = status_code
        super().__init__(
            f"Delivery failed for {target_url} (status={status_code})",
            code="DELIVERY_FAILED",
        )


class QueueFullError(AppError):
    """Raised when the event queue is full."""

    def __init__(self, queue_size: int) -> None:
        self.queue_size = queue_size
        super().__init__(
            f"Queue is full (size={queue_size})",
            code="QUEUE_FULL",
        )


class ShutdownTimeoutError(AppError):
    """Raised when graceful shutdown times out."""

    def __init__(self, pending_tasks: int) -> None:
        self.pending_tasks = pending_tasks
        super().__init__(
            f"Shutdown timed out with {pending_tasks} pending tasks",
            code="SHUTDOWN_TIMEOUT",
        )
