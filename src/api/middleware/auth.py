import re
from typing import Any, Callable

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()

API_KEY_PATTERN = re.compile(r"^sk-[a-zA-Z0-9-]{20,}$")

MOCK_API_KEYS: dict[str, dict[str, str]] = {
    "sk-free-key-for-testing-1234567": {"tier": "free"},
    "sk-pro-key-for-testing-12345678": {"tier": "pro"},
    "sk-enterprise-key-test-123456789": {"tier": "enterprise"},
    "sk-1234567890abcdef1234567890abcd": {"tier": "free"},
}


def validate_api_key_format(api_key: str | None) -> bool:
    if not api_key:
        return False
    return bool(API_KEY_PATTERN.match(api_key))


async def validate_api_key(api_key: str) -> dict[str, Any] | None:
    return MOCK_API_KEYS.get(api_key)


def get_rate_limit_for_tier(tier: str) -> int:
    limits = {
        "free": 100,
        "pro": 2000,
        "enterprise": 0,
    }
    return limits.get(tier.lower(), 100)


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
        # Support both dict-based key data and legacy/proxy string-based data.
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
