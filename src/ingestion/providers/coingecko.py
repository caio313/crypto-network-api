from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from src.core.config import settings
from src.core.logging import structlog
from src.ingestion.providers.defillama import (
    CircuitState,
    CircuitBreaker,
    get_circuit_breaker,
)

logger = structlog.get_logger()


COINGECKO_IDS: dict[str, str] = {
    "solana": "solana",
    "ethereum": "ethereum",
    "polygon": "matic-network",
    "arbitrum": "arbitrum-one",
    "base": "base",
    "optimism": "optimism",
    "avalanche": "avalanche-2",
    "bsc": "binancecoin",
}


async def get_gas_prices() -> dict[str, dict[str, float]]:
    circuit = get_circuit_breaker("coingecko_gas")
    
    if not circuit.can_execute():
        logger.warning("circuit_breaker_open", provider="coingecko_gas")
        raise httpx.HTTPStatusError(
            "Circuit breaker is open",
            request=httpx.Request("GET", "coingecko/gas"),
            response=httpx.Response(503),
        )
    
    params: dict[str, str] = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": "1",
        "page": "1",
        "sparkline": "false",
    }
    
    headers: dict[str, str] = {}
    if settings.coingecko_api_key:
        headers["x-cg-demo-api-key"] = settings.coingecko_api_key
    
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            response = await client.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            
        circuit.record_success()
        logger.info("coingecko_gas_fetched")
        return {}
        
    except httpx.HTTPStatusError as e:
        circuit.record_failure()
        logger.error("coingecko_gas_http_error", status=e.response.status_code)
        raise
    except httpx.TimeoutException:
        circuit.record_failure()
        logger.error("coingecko_gas_timeout")
        raise
    except Exception as e:
        circuit.record_failure()
        logger.error("coingecko_gas_error", error=str(e))
        raise


async def get_token_price(network: str, token: str = "usd-coin") -> dict[str, dict[str, float]]:
    circuit = get_circuit_breaker(f"coingecko_price_{network}")
    
    if not circuit.can_execute():
        raise httpx.HTTPStatusError(
            "Circuit breaker is open",
            request=httpx.Request("GET", "coingecko/price"),
            response=httpx.Response(503),
        )
    
    coingecko_id = COINGECKO_IDS.get(network)
    if not coingecko_id:
        logger.warning("unknown_network_coingecko", network=network)
        return {}
    
    params: dict[str, str | bool] = {
        "ids": coingecko_id,
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }
    
    headers: dict[str, str] = {}
    if settings.coingecko_api_key:
        headers["x-cg-demo-api-key"] = settings.coingecko_api_key
    
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            response = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            
        circuit.record_success()
        logger.info("coingecko_price_fetched", network=network)
        return data
        
    except httpx.HTTPStatusError as e:
        circuit.record_failure()
        logger.error("coingecko_price_http_error", network=network, status=e.response.status_code)
        raise
    except httpx.TimeoutException:
        circuit.record_failure()
        logger.error("coingecko_price_timeout", network=network)
        raise
    except Exception as e:
        circuit.record_failure()
        logger.error("coingecko_price_error", network=network, error=str(e))
        raise


async def get_network_data(networks: list[str] | None = None) -> dict[str, dict[str, Any]]:
    circuit = get_circuit_breaker("coingecko_networks")
    
    if not circuit.can_execute():
        raise httpx.HTTPStatusError(
            "Circuit breaker is open",
            request=httpx.Request("GET", "coingecko/networks"),
            response=httpx.Response(503),
        )
    
    if networks is None:
        networks = list(COINGECKO_IDS.keys())
    
    ids = [COINGECKO_IDS[n] for n in networks if n in COINGECKO_IDS]
    
    if not ids:
        return {}
    
    params: dict[str, str] = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": str(len(ids)),
        "page": "1",
        "sparkline": "false",
        "price_change_percentage": "24h,7d",
    }
    
    headers: dict[str, str] = {}
    if settings.coingecko_api_key:
        headers["x-cg-demo-api-key"] = settings.coingecko_api_key
    
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            response = await client.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            
        circuit.record_success()
        
        result: dict[str, dict[str, Any]] = {}
        for coin in data:
            for network, coingecko_id in COINGECKO_IDS.items():
                if coin.get("id") == coingecko_id:
                    result[network] = {
                        "price": coin.get("current_price", 0),
                        "change_24h": coin.get("price_change_percentage_24h", 0),
                        "change_7d": coin.get("price_change_percentage_7d_in_currency", 0),
                        "market_cap": coin.get("market_cap", 0),
                        "volume_24h": coin.get("total_volume", 0),
                    }
                    break
        
        logger.info("coingecko_networks_fetched", networks=len(result))
        return result
        
    except httpx.HTTPStatusError as e:
        circuit.record_failure()
        logger.error("coingecko_networks_http_error", status=e.response.status_code)
        raise
    except httpx.TimeoutException:
        circuit.record_failure()
        logger.error("coingecko_networks_timeout")
        raise
    except Exception as e:
        circuit.record_failure()
        logger.error("coingecko_networks_error", error=str(e))
        raise
