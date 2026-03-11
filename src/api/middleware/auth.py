import hashlib
import re
from dataclasses import dataclass
from typing import Any, Callable

import structlog
from fastapi import Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import settings
from src.core.logging import structlog as logging_module

logger = structlog.get_logger()

API_KEY_PATTERN = re.compile(r"^sk-[a-zA-Z0-9]{32,}$")


@dataclass
class APIKeyTier:
    name: str
    requests_per_minute: int


TIER_CONFIG: dict[str, APIKeyTier] = {
    "free": APIKeyTier("free", 60),
    "basic": APIKeyTier("basic", 300),
    "premium": APIKeyTier("premium", 1000),
    "pro": APIKeyTier("pro", 5000),
    "enterprise": APIKeyTier("enterprise", 999999),
}


MOCK_API_KEYS: dict[str, str] = {
    "sk-1234567890abcdef1234567890abcd": "free",
    "sk-abcdef1234567890abcdef123456": "basic",
}


def hash_api_key(api_key: str) -> str:
    salt = settings.api_secret_key or "default-salt-change-me"
    combined = f"{salt}:{api_key}"
    return hashlib.sha256(combined.encode()).hexdigest()


def validate_api_key_format(api_key: str | None) -> bool:
    if not api_key:
        return False
    return bool(API_KEY_PATTERN.match(api_key))


async def validate_api_key(key: str) -> dict | None:
    if not validate_api_key_format(key):
        return None

    tier = MOCK_API_KEYS.get(key)
    if tier is None:
        return None

    return {"tier": tier}


async def get_api_key_tier(x_api_key: str | None = Header(None)) -> str:
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key",
        )

    result = await validate_api_key(x_api_key)
    if not result:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )

    key_hash = hash_api_key(x_api_key)

    tier = result.get("tier")
    if not isinstance(tier, str):
        tier = "free"

    logger.info("api_key_validated", tier=tier, key_hash=key_hash[:8])
    return tier


def get_rate_limit_for_tier(tier: str) -> int:
    tier_config = TIER_CONFIG.get(tier)
    if tier_config:
        return tier_config.requests_per_minute
    return TIER_CONFIG["free"].requests_per_minute


class AuthMiddleware(BaseHTTPMiddleware):
    EXEMPT_PATHS = {"/", "/docs", "/redoc", "/openapi.json", "/health", "/metrics"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        api_key = request.headers.get("x-api-key")

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing API key"},
            )

        result = await validate_api_key(api_key)
        if not result:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key"},
            )

        tier = result.get("tier")
        request.state.tier = tier

        return await call_next(request)
