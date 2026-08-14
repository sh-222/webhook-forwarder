"""Webhook sender with exponential backoff."""

from __future__ import annotations

import asyncio
import random

from core.exceptions import WebhookDeliveryError
from core.logging import get_logger
from core.settings import settings
from domain.entities import Event
from domain.protocols import HttpClientProtocol, RateLimiterProtocol

logger = get_logger(__name__)


class WebhookSender:
    """Sends webhook events with rate limiting and exponential backoff."""

    def __init__(
        self,
        http_client: HttpClientProtocol,
        rate_limiter: RateLimiterProtocol,
    ) -> None:
        self._http = http_client
        self._rate_limiter = rate_limiter
        self._base_delay = settings.base_delay
        self._max_delay = settings.max_delay

    def _calculate_backoff(self, retry_count: int) -> float:
        """Calculate exponential backoff with jitter."""
        delay = min(self._base_delay * (2**retry_count), self._max_delay)
        jitter = random.uniform(0, delay * 0.1)  # 10% jitter
        return delay + jitter

    async def send(self, event: Event) -> None:
        """Send a single event with rate limiting and backoff.

        Raises:
            WebhookDeliveryError: If delivery fails after rate limit allows.
        """
        # Rate limiting
        allowed = await self._rate_limiter.acquire(event.target_url)
        if not allowed:
            # Wait and retry once
            await asyncio.sleep(self._calculate_backoff(event.retry_count))
            allowed = await self._rate_limiter.acquire(event.target_url)
            if not allowed:
                raise WebhookDeliveryError(
                    target_url=event.target_url, status_code=None
                )

        # Send
        try:
            status_code, body = await self._http.post(event.target_url, event.payload)

            if status_code >= 400:
                raise WebhookDeliveryError(
                    target_url=event.target_url, status_code=status_code
                )

            logger.info(
                "webhook_delivered",
                event_id=str(event.event_id),
                target_url=event.target_url,
                status_code=status_code,
            )

        except WebhookDeliveryError:
            raise

        except Exception as exc:
            logger.error(
                "webhook_delivery_error",
                event_id=str(event.event_id),
                target_url=event.target_url,
                error=str(exc),
            )
            raise WebhookDeliveryError(target_url=event.target_url) from exc
