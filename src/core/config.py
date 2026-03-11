from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_secret_key: str = ""
    debug: bool = False
    environment: str = "development"

    database_url: str = ""

    redis_url: str = "redis://localhost:6379/0"

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    coingecko_api_key: str = ""
    defillama_base_url: str = "https://api.llama.fi"

    mcp_server_host: str = "0.0.0.0"
    mcp_server_port: int = 8001

    http_timeout: float = 5.0
    circuit_breaker_threshold: int = 3
    circuit_breaker_recovery_seconds: int = 60


settings = Settings()
