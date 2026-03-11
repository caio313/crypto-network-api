import os
import pytest
from unittest.mock import AsyncMock, MagicMock

os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["ENVIRONMENT"] = "test"


@pytest.fixture
def mock_redis():
    from src.cache.redis import RedisClient

    mock = MagicMock(spec=RedisClient)
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.get_gas_prices = AsyncMock(return_value={})
    mock.get_network_scores = AsyncMock(return_value=None)
    mock.get_tvl_data = AsyncMock(return_value={})
    mock.get_alerts = AsyncMock(return_value={"alerts": []})
    mock.get_gas_history = AsyncMock(return_value=None)
    mock.get_tvl_history = AsyncMock(return_value=None)
    mock.get_network_status = AsyncMock(return_value=None)

    return mock


@pytest.fixture
def app_with_mock_redis(mock_redis):
    from src.main import app
    from src.cache import redis as redis_module
    from src.api.middleware import auth as auth_module

    redis_module.redis_client = mock_redis

    from unittest.mock import patch

    async def _mock_validate_api_key(key: str):
        explicit = {
            "sk-free-key-for-testing-1234567": {"tier": "free"},
            "sk-pro-key-for-testing-12345678": {"tier": "pro"},
            "sk-enterprise-key-test-123456789": {"tier": "enterprise"},
            "sk-1234567890abcdef1234567890abcd": {"tier": "free"},
        }
        return explicit.get(key)

    patcher = patch("src.api.middleware.auth.validate_api_key", new=_mock_validate_api_key)
    patcher.start()
    try:
        yield app
    finally:
        patcher.stop()
