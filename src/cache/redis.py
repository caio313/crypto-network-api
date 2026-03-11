import json
from typing import Any

import redis.asyncio as redis

from src.cache import ttl as ttl_constants
from src.core.config import settings
from src.core.logging import structlog

logger = structlog.get_logger()


class RedisClient:
    def __init__(self) -> None:
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        self._client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("redis_connected", url=settings.redis_url)

    async def disconnect(self) -> None:
        if self._client:
            await self._client.close()
            logger.info("redis_disconnected")

    @property
    def client(self) -> redis.Redis:
        if not self._client:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._client

    async def get(self, key: str) -> dict[str, Any] | None:
        try:
            data = await self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error("redis_get_error", key=key, error=str(e))
            return None

    async def set(
        self,
        key: str,
        value: dict[str, Any],
        ex: int | None = None,
    ) -> bool:
        try:
            serialized = json.dumps(value)
            await self.client.set(key, serialized, ex=ex)
            return True
        except Exception as e:
            logger.error("redis_set_error", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error("redis_delete_error", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error("redis_exists_error", key=key, error=str(e))
            return False

    async def get_json(self, key: str) -> dict[str, Any] | None:
        return await self.get(key)

    async def set_json(
        self,
        key: str,
        value: dict[str, Any],
        ttl: int,
    ) -> bool:
        return await self.set(key, value, ex=ttl)

    async def get_network_scores(self) -> dict[str, Any] | None:
        return await self.get("network:scores")

    async def set_network_scores(self, scores: dict[str, Any]) -> bool:
        return await self.set_json(
            "network:scores",
            scores,
            ttl_constants.TTL_NETWORK_SCORE,
        )

    async def get_tvl_data(self) -> dict[str, float] | None:
        return await self.get("tvl:data")

    async def set_tvl_data(self, tvl_data: dict[str, float]) -> bool:
        return await self.set_json(
            "tvl:data",
            tvl_data,
            ttl_constants.TTL_TVL,
        )

    async def get_gas_prices(self) -> dict[str, Any] | None:
        return await self.get("gas:current")

    async def set_gas_prices(self, gas_data: dict[str, Any]) -> bool:
        return await self.set_json(
            "gas:current",
            gas_data,
            ttl_constants.TTL_GAS_CURRENT,
        )

    async def get_alerts(self) -> dict[str, Any] | None:
        return await self.get("alerts:active")

    async def set_alerts(self, alerts: list[dict[str, Any]]) -> bool:
        return await self.set(
            "alerts:active",
            {"alerts": alerts},
            ex=ttl_constants.TTL_INCIDENTS,
        )

    async def get_gas_history(self, network: str) -> dict[str, Any] | None:
        return await self.get(f"gas:history:{network}")

    async def set_gas_history(self, network: str, history: list[dict[str, Any]]) -> bool:
        return await self.set(
            f"gas:history:{network}",
            {"history": history},
            ex=ttl_constants.TTL_HISTORICAL,
        )

    async def get_tvl_history(self, network: str) -> dict[str, Any] | None:
        return await self.get(f"tvl:history:{network}")

    async def set_tvl_history(self, network: str, history: list[dict[str, Any]]) -> bool:
        return await self.set(
            f"tvl:history:{network}",
            {"history": history},
            ex=ttl_constants.TTL_HISTORICAL,
        )

    async def get_network_status(self) -> dict[str, Any] | None:
        return await self.get("network:status")

    async def set_network_status(self, status: dict[str, Any]) -> bool:
        return await self.set_json(
            "network:status",
            status,
            ttl_constants.TTL_UPTIME,
        )


redis_client = RedisClient()
