import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Callable

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.middleware.auth import get_rate_limit_for_tier
from src.cache.redis import redis_client
from src.core.logging import structlog

logger = structlog.get_logger()


DAILY_RATE_LIMITS = {
    "free": 100,
    "pro": 2000,
    "enterprise": 0,
}

TTL_RATE_LIMIT = 86400


def get_today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_midnight_utc_timestamp() -> int:
    now = datetime.now(timezone.utc)
    tomorrow = now + timedelta(days=1)
    midnight = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(midnight.timestamp())


async def check_trial_status(api_key: str, current_tier: str) -> tuple[str, datetime | None]:
    if current_tier.lower() != "pro":
        return current_tier, None

    trial_key = f"trial:{api_key}"
    trial_data = await redis_client.get(trial_key)

    if trial_data:
        trial_expires_str = trial_data.get("trial_expires_at")
        if trial_expires_str:
            trial_expires = datetime.fromisoformat(trial_expires_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)

            if trial_expires > now:
                return "pro", trial_expires
            else:
                has_card = trial_data.get("has_payment_method", False)
                if not has_card:
                    logger.info("trial_expired_downgrading", key=api_key[:8])
                    return "free", None

    return current_tier, None


async def activate_trial(api_key: str) -> datetime:
    trial_key = f"trial:{api_key}"
    now = datetime.now(timezone.utc)
    trial_expires = now + timedelta(days=30)

    await redis_client.set(
        trial_key,
        {
            "trial_expires_at": trial_expires.isoformat(),
            "has_payment_method": False,
            "registered_at": now.isoformat(),
        },
        ex=60 * 60 * 24 * 35,
    )

    logger.info("trial_activated", key=api_key[:8], expires=trial_expires.isoformat())
    return trial_expires


@dataclass
class RateLimitEntry:
    count: int
    reset_time: float


class RateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, RateLimitEntry] = defaultdict(
            lambda: RateLimitEntry(count=0, reset_time=0.0)
        )

    async def check_rate_limit(self, key: str, tier: str) -> tuple[bool, int, str]:
        current_tier = tier

        if tier.lower() == "pro":
            current_tier, trial_expires = await check_trial_status(key, tier)
            if trial_expires:
                current_tier = "pro"

        limit = DAILY_RATE_LIMITS.get(current_tier.lower(), DAILY_RATE_LIMITS["free"])

        if limit == 0:
            return True, 0, current_tier

        today = get_today_key()
        redis_key = f"rate_limit:{key}:{today}"

        try:
            current_count = await redis_client.client.get(redis_key)
            if current_count is None:
                count = 1
            else:
                count = int(current_count) + 1

            await redis_client.client.set(redis_key, str(count), ex=TTL_RATE_LIMIT)

        except Exception as e:
            logger.warning("redis_rate_limit_error", error=str(e))
            entry = self._buckets[key]
            current_time = time.time()
            if current_time > entry.reset_time:
                entry.count = 0
                entry.reset_time = get_midnight_utc_timestamp()
            entry.count += 1
            count = entry.count

        remaining = max(0, limit - count)
        reset_timestamp = get_midnight_utc_timestamp()

        if count > limit:
            logger.warning(
                "rate_limit_exceeded",
                key=key[:8],
                limit=limit,
                current=count,
            )
            return False, 0, current_tier

        return True, remaining, current_tier

    def get_headers(self, remaining: int, tier: str) -> dict[str, str]:
        limit = DAILY_RATE_LIMITS.get(tier.lower(), DAILY_RATE_LIMITS["free"])
        reset_timestamp = get_midnight_utc_timestamp()

        return {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_timestamp),
            "X-Plan-Tier": tier.upper(),
        }


rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in ["/docs", "/openapi.json", "/redoc", "/health", "/", "/metrics"]:
            return await call_next(request)

        tier = getattr(request.state, "tier", "FREE")

        if tier is None:
            tier = "FREE"

        api_key = request.headers.get(
            "x-api-key", request.client.host if request.client else "anonymous"
        )
        allowed, remaining, current_tier = await rate_limiter.check_rate_limit(api_key, tier)

        if not allowed:
            reset_timestamp = get_midnight_utc_timestamp()
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={
                    "Retry-After": "86400",
                    **rate_limiter.get_headers(0, current_tier),
                },
            )

        response = await call_next(request)

        headers = rate_limiter.get_headers(remaining, current_tier)
        for key, value in headers.items():
            response.headers[key] = value

        return response
