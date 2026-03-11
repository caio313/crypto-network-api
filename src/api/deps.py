from typing import Annotated

from fastapi import Depends, Request

from src.cache.redis import RedisClient, redis_client


async def get_redis_client() -> RedisClient:
    return redis_client


CacheDep = Annotated[RedisClient, Depends(get_redis_client)]


async def get_tier(request: Request) -> str:
    tier = getattr(request.state, 'tier', 'free')
    if tier is None:
        tier = "free"
    return tier.lower()


TierDep = Annotated[str, Depends(get_tier)]
