"""
Reusable rate-limiting dependency for FastAPI routes.

Backed by ``redis_client`` (Redis when configured, TTL-honoring in-memory
fallback otherwise) so every development/demo instance still enforces limits.
"""

from typing import Callable, Optional

from fastapi import Request
from starlette.concurrency import run_in_threadpool

from app.services.errors import RateLimitedError
from app.services.redis_service import redis_client


def _key_for(request: Request, key_prefix: str, scope: str) -> str:
    client_ip = request.client.host if request.client else "unknown"
    return f"ratelimit:{key_prefix}:{scope}:{client_ip}"


class RateLimiter:
    def __init__(
        self,
        *,
        limit: int,
        window_seconds: int,
        prefix: str,
        scope: Optional[Callable[[Request], str]] = None,
    ):
        self.limit = limit
        self.window_seconds = window_seconds
        self.prefix = prefix
        self.scope_fn = scope or (lambda request: "default")

    async def __call__(self, request: Request) -> None:
        key = _key_for(request, self.prefix, self.scope_fn(request))
        allowed = await run_in_threadpool(
            redis_client.rate_limit_check, key, self.limit, self.window_seconds
        )
        if not allowed:
            raise RateLimitedError(
                f"Too many requests. The limit is {self.limit} per "
                f"{self.window_seconds}s. Try again shortly."
            )


# A conservative global write-limit: 120 requests / minute per client.
global_write_limiter = RateLimiter(
    limit=120, window_seconds=60, prefix="global-write"
)