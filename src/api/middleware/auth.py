import re
from typing import Any, Callable

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import select
from src.db.session import AsyncSessionLocal
from src.models.db.api_keys import ApiKey

logger = structlog.get_logger()

API_KEY_PATTERN = re.compile(r"^sk-[a-zA-Z0-9-]{20,}$")


def validate_api_key_format(api_key: str | None) -> bool:
    if not api_key:
        return False
    return bool(API_KEY_PATTERN.match(api_key))


async def validate_api_key(api_key: str) -> dict[str, Any] | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ApiKey).where(ApiKey.key == api_key, ApiKey.is_active == True)
        )
        key_obj = result.scalar_one_or_none()
        if key_obj is None:
            return None
        return {"tier": key_obj.tier}


def get_rate_limit_for_tier(tier: str) -> int:
    limits = {
        "free": 100,
        "pro": 2000,
        "enterprise": 0,
    }
    return limits.get(tier.lower(), 100)


class AuthMiddleware(BaseHTTPMiddleware):
    EXEMPT_PATHS = {
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/metrics",
        "/v1/auth/register",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        api_key = request.headers.get("x-api-key")

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing API key"},
            )

        if not validate_api_key_format(api_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key format"},
            )

        key_data = await validate_api_key(api_key)
        if key_data is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key"},
            )

        if isinstance(key_data, dict) and "tier" in key_data:
            tier = key_data["tier"]
        elif isinstance(key_data, str):
            tier = key_data
        else:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key"},
            )

        request.state.tier = tier
        logger.info("api_key_validated", tier=tier, key_prefix=api_key[:8])
        return await call_next(request)
