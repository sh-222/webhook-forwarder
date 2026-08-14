"""HTTP client adapter using httpx."""

from __future__ import annotations

import httpx

from core.logging import get_logger
from core.settings import settings

logger = get_logger(__name__)


class HttpClient:
    """Async HTTP client wrapper using httpx."""

    def __init__(self, timeout: float | None = None) -> None:
        self._timeout = timeout or settings.http_timeout
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Lazy-init the httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                follow_redirects=True,
            )
        return self._client

    async def post(self, url: str, payload: dict) -> tuple[int, str]:
        """Send POST request with JSON payload.

        Returns:
            (status_code, response_body)
        """
        client = await self._ensure_client()

        logger.info("http_post_started", url=url)

        try:
            response = await client.post(url, json=payload)
            body = response.text

            logger.info(
                "http_post_completed",
                url=url,
                status_code=response.status_code,
                body_length=len(body),
            )

            return response.status_code, body

        except httpx.TimeoutException as exc:
            logger.error("http_post_timeout", url=url, error=str(exc))
            raise

        except httpx.RequestError as exc:
            logger.error("http_post_error", url=url, error=str(exc))
            raise

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("http_client_closed")
