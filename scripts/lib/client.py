"""Serper API client with rate limiting and retry logic."""

import asyncio
import time
import logging
import aiohttp
from typing import List, Dict, Any, Optional

from .models import Query

logger = logging.getLogger("serper")


class SerperAPIError(Exception):
    pass


class RateLimiter:
    """Token bucket rate limiter."""
    def __init__(self, rate: int):
        self.rate = rate
        self.tokens = rate
        self.last_update = time.perf_counter()
        self.lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1):
        async with self.lock:
            while tokens > self.tokens:
                now = time.perf_counter()
                elapsed = now - self.last_update
                self.tokens = min(self.rate, self.tokens + elapsed * self.rate)
                self.last_update = now
                if tokens > self.tokens:
                    await asyncio.sleep((tokens - self.tokens) / self.rate)
            self.tokens -= tokens


class SerperClient:
    """Async client for Serper Places API with rate limiting."""

    def __init__(self, api_key: str, rate_limit: int = 100):
        self.api_key = api_key
        self.rate_limiter = RateLimiter(rate_limit)
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = "https://google.serper.dev"

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json",
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def batch_search_places(self, queries: List[Query], max_retries: int = 3) -> List[Dict[str, Any]]:
        """Execute a batch of place search queries with retry logic."""
        if not self.session:
            raise SerperAPIError("Session not initialized. Use 'async with'.")

        api_queries = [q.to_dict() for q in queries]
        await self.rate_limiter.acquire(len(queries))

        for attempt in range(max_retries):
            try:
                async with self.session.post(
                    f"{self.base_url}/places",
                    json=api_queries,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    if resp.status == 429:
                        retry = int(resp.headers.get("Retry-After", "60"))
                        if attempt < max_retries - 1:
                            logger.warning(f"Rate limited, retrying in {retry}s...")
                            await asyncio.sleep(retry)
                            continue
                        raise SerperAPIError(f"Rate limit exceeded. Retry after {retry}s.")
                    raise SerperAPIError(f"API error {resp.status}: {await resp.text()}")
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    logger.warning(f"Timeout on attempt {attempt + 1}, retrying...")
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise SerperAPIError("Request timeout after retries")
            except aiohttp.ClientError as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise SerperAPIError(f"Network error: {e}")

        raise SerperAPIError("Max retries exceeded")
