from typing import Any

import httpx

from src.core.config import settings
from src.core.logging import structlog
from src.ingestion.providers.defillama import (
    get_circuit_breaker,
)

logger = structlog.get_logger()


GAS_API_URL = "https://api.blocknative.com/v0"


async def get_gas_estimates() -> dict[str, Any]:
    circuit = get_circuit_breaker("gasnow")
    
    if not circuit.can_execute():
        logger.warning("circuit_breaker_open", provider="gasnow")
        raise httpx.HTTPStatusError(
            "Circuit breaker is open",
            request=httpx.Request("GET", "gasnow"),
            response=httpx.Response(503),
        )
    
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            response = await client.get(
                "https://api.blocknative.com/gasprices/blockprices"
            )
            response.raise_for_status()
            data = response.json()
            
        circuit.record_success()
        
        result: dict[str, Any] = {
            "networks": {},
            "timestamp": data.get("timestamp", ""),
        }
        
        for block_price in data.get("blockPrices", []):
            chain = block_price.get("chain", "ethereum")
            if chain == "ethereum":
                result["networks"]["ethereum"] = {
                    "base_fee": block_price.get("baseFeeSuggested", {}),
                    "priority_fee": block_price.get("priorityFeeSuggestions", []),
                    "estimated_confirmed_blocks": block_price.get("estimatedConfirmedBlocks", 0),
                }
        
        logger.info("gasnow_data_fetched")
        return result
        
    except httpx.HTTPStatusError as e:
        circuit.record_failure()
        logger.error("gasnow_http_error", status=e.response.status_code)
        raise
    except httpx.TimeoutException:
        circuit.record_failure()
        logger.error("gasnow_timeout")
        raise
    except Exception as e:
        circuit.record_failure()
        logger.error("gasnow_error", error=str(e))
        raise


async def get_eth_gas_prices() -> dict[str, float]:
    circuit = get_circuit_breaker("eth_gas")
    
    if not circuit.can_execute():
        logger.warning("circuit_breaker_open", provider="eth_gas")
        raise httpx.HTTPStatusError(
            "Circuit breaker is open",
            request=httpx.Request("GET", "eth_gas"),
            response=httpx.Response(503),
        )
    
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            response = await client.get(
                "https://api.etherscan.io/api?module=gastracker&action=gasoracle"
            )
            response.raise_for_status()
            data = response.json()
            
        circuit.record_success()
        
        result: dict[str, float] = {}
        if data.get("status") == "1":
            result_data = data.get("result", {})
            result = {
                "safe": float(result_data.get("SafeGasPrice", 0)),
                "propose": float(result_data.get("ProposeGasPrice", 0)),
                "fast": float(result_data.get("FastGasPrice", 0)),
            }
        
        logger.info("eth_gas_fetched", result=result)
        return result
        
    except httpx.HTTPStatusError as e:
        circuit.record_failure()
        logger.error("eth_gas_http_error", status=e.response.status_code)
        raise
    except httpx.TimeoutException:
        circuit.record_failure()
        logger.error("eth_gas_timeout")
        raise
    except Exception as e:
        circuit.record_failure()
        logger.error("eth_gas_error", error=str(e))
        raise
