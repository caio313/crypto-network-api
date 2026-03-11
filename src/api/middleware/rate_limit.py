import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.middleware.auth import get_rate_limit_for_tier
from src.core.logging import structlog

logger = structlog.get_logger()


@dataclass
class RateLimitEntry:
    count: int
    reset_time: float


class RateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, RateLimitEntry] = defaultdict(
            lambda: RateLimitEntry(count=0, reset_time=0.0)
        )

    def check_rate_limit(self, key: str, limit: int) -> tuple[bool, int]:
        current_time = time.time()
        entry = self._buckets[key]

        if current_time > entry.reset_time:
            entry.count = 0
            entry.reset_time = current_time + 60

        entry.count += 1

        remaining = max(0, limit - entry.count)
        retry_after = int(entry.reset_time - current_time) + 1

        if entry.count > limit:
            logger.warning(
                "rate_limit_exceeded",
                key=key[:8],
                limit=limit,
                current=entry.count,
            )
            return False, retry_after

        return True, remaining

    def get_headers(self, key: str, limit: int, remaining: int, tier: str = "FREE") -> dict[str, str]:
        entry = self._buckets[key]
        return {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(entry.reset_time)),
            "X-Plan-Tier": tier,
        }


rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in ["/docs", "/openapi.json", "/redoc", "/health", "/", "/metrics"]:
            return await call_next(request)

        tier = getattr(request.state, 'tier', 'FREE')
        
        if tier is None:
            tier = "FREE"
        
        rate_limit = get_rate_limit_for_tier(tier.lower())

        api_key = request.headers.get("x-api-key", request.client.host if request.client else "anonymous")
        allowed, retry_after = rate_limiter.check_rate_limit(api_key, rate_limit)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={
                    "Retry-After": str(retry_after),
                    **rate_limiter.get_headers(api_key, rate_limit, 0, tier),
                },
            )

        response = await call_next(request)

        _, remaining = rate_limiter.check_rate_limit(api_key, rate_limit)
        headers = rate_limiter.get_headers(api_key, rate_limit, remaining, tier)
        for key, value in headers.items():
            response.headers[key] = value

        return response
