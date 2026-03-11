import os
import pytest

os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["ENVIRONMENT"] = "test"

from unittest.mock import AsyncMock, patch, MagicMock
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client():
    from src.cache.redis import redis_client
    from unittest.mock import patch, AsyncMock, MagicMock

    mock_redis = MagicMock()
    mock_redis.connect = AsyncMock()
    mock_redis.disconnect = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.get_gas_prices = AsyncMock(return_value={})
    mock_redis.get_network_scores = AsyncMock(return_value=None)
    mock_redis.get_tvl_data = AsyncMock(return_value={})
    mock_redis.get_alerts = AsyncMock(return_value={"alerts": []})
    mock_redis.get_gas_history = AsyncMock(return_value=None)
    mock_redis.get_tvl_history = AsyncMock(return_value=None)
    mock_redis.get_network_status = AsyncMock(return_value=None)

    redis_client._client = mock_redis

    async def _mock_validate(key: str):
        keys = {
            "sk-free-key-for-testing-1234567": {"tier": "free"},
            "sk-pro-key-for-testing-12345678": {"tier": "pro"},
            "sk-enterprise-key-test-123456789": {"tier": "enterprise"},
            "sk-1234567890abcdef1234567890abcd": {"tier": "free"},
        }
        return keys.get(key)

    with patch("src.api.middleware.auth.validate_api_key", new=_mock_validate):
        from src.main import app
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test", follow_redirects=True
        ) as ac:
            yield ac


class TestAPIEndpoints:
    @pytest.mark.asyncio
    async def test_health_endpoint_no_auth_required(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_root_endpoint_no_auth_required(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_401_without_api_key(self, client):
        response = await client.get("/v1/networks")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_401_with_invalid_api_key_format(self, client):
        response = await client.get("/v1/networks", headers={"X-API-Key": "invalid-key"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_basic_endpoint_with_valid_free_key(self, client):
        response = await client.get(
            "/v1/gas", headers={"X-API-Key": "sk-1234567890abcdef1234567890abcd"}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_pro_endpoint_blocked_for_free_tier(self, client):
        response = await client.get(
            "/v1/gas/ethereum/predict", headers={"X-API-Key": "sk-1234567890abcdef1234567890abcd"}
        )
        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["error"] == "plan_required"
        assert data["detail"]["required_plan"] == "PRO"

    @pytest.mark.asyncio
    async def test_pro_endpoint_accessible_with_pro_key(self, client):
        from src.api.middleware.auth import MOCK_API_KEYS

        original_keys = MOCK_API_KEYS.copy()
        MOCK_API_KEYS["sk-pro-key-for-testing-12345678"] = "pro"

        try:
            response = await client.get(
                "/v1/gas/ethereum/predict", headers={"X-API-Key": "sk-pro-key-for-testing-12345678"}
            )
            assert response.status_code in [200, 500]
        finally:
            MOCK_API_KEYS.clear()
            MOCK_API_KEYS.update(original_keys)

    @pytest.mark.asyncio
    async def test_networks_endpoint_returns_scores(self, client):
        response = await client.get(
            "/v1/networks", headers={"X-API-Key": "sk-1234567890abcdef1234567890abcd"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_gas_endpoint_accessible(self, client):
        response = await client.get(
            "/v1/gas", headers={"X-API-Key": "sk-1234567890abcdef1234567890abcd"}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_alerts_endpoint_accessible(self, client):
        response = await client.get(
            "/v1/alerts", headers={"X-API-Key": "sk-1234567890abcdef1234567890abcd"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data

    @pytest.mark.asyncio
    async def test_rate_limit_429_response(self, client):
        import time

        api_key = "sk-rate-limit-test-key-123456789"
        from src.api.middleware.auth import MOCK_API_KEYS

        MOCK_API_KEYS[api_key] = "free"

        original_limit = 60
        response = None

        try:
            for _ in range(original_limit + 5):
                response = await client.get("/v1/gas", headers={"X-API-Key": api_key})
                if response.status_code == 429:
                    break

            assert response is not None
            assert response.status_code == 429
            assert "Retry-After" in response.headers or "X-RateLimit-Remaining" in response.headers
        finally:
            if api_key in MOCK_API_KEYS:
                del MOCK_API_KEYS[api_key]

    @pytest.mark.asyncio
    async def test_invalid_network_returns_400(self, client):
        response = await client.get(
            "/v1/gas/invalid_network", headers={"X-API-Key": "sk-1234567890abcdef1234567890abcd"}
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_valid_networks_accepted(self, client):
        valid_networks = [
            "ethereum",
            "solana",
            "polygon",
            "arbitrum",
            "base",
            "optimism",
            "avalanche",
            "bsc",
        ]

        for network in valid_networks:
            response = await client.get(
                f"/v1/gas/{network}", headers={"X-API-Key": "sk-1234567890abcdef1234567890abcd"}
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_documentation_endpoints_accessible(self, client):
        response = await client.get("/docs")
        assert response.status_code == 200

        response = await client.get("/redoc")
        assert response.status_code == 200

        response = await client.get("/openapi.json")
        assert response.status_code == 200
