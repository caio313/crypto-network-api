from typing import Any

import httpx

from src.core.config import settings
from src.core.logging import structlog
from src.ingestion.providers.defillama import (
    CircuitBreaker,
    get_circuit_breaker,
)

logger = structlog.get_logger()


async def get_l2_security_data() -> dict[str, dict[str, Any]]:
    circuit = get_circuit_breaker("l2beat")
    
    if not circuit.can_execute():
        logger.warning("circuit_breaker_open", provider="l2beat")
        raise httpx.HTTPStatusError(
            "Circuit breaker is open",
            request=httpx.Request("GET", "l2beat"),
            response=httpx.Response(503),
        )
    
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            response = await client.get(
                "https://l2beat.com/api/scaling/tvl"
            )
            response.raise_for_status()
            data = response.json()
            
        circuit.record_success()
        
        result: dict[str, dict[str, Any]] = {}
        network_mapping = {
            "arbitrum": "Arbitrum One",
            "optimism": "Optimism",
            "base": "Base",
            "polygon": "Polygon",
        }
        
        for item in data.get("projects", []):
            project_name = item.get("name", "")
            for network_id, display_name in network_mapping.items():
                if display_name.lower() in project_name.lower():
                    result[network_id] = {
                        "tvl": item.get("tvl", {}).get("total", {}).get("usd", 0),
                        "cvv": item.get("cvv", ""),
                        "risk": item.get("risk", {}),
                        "type": item.get("category", ""),
                    }
                    break
        
        logger.info("l2beat_data_fetched", networks=len(result))
        return result
        
    except httpx.HTTPStatusError as e:
        circuit.record_failure()
        logger.error("l2beat_http_error", status=e.response.status_code)
        raise
    except httpx.TimeoutException:
        circuit.record_failure()
        logger.error("l2beat_timeout")
        raise
    except Exception as e:
        circuit.record_failure()
        logger.error("l2beat_error", error=str(e))
        raise


async def get_l2_risk_data() -> dict[str, dict[str, Any]]:
    circuit = get_circuit_breaker("l2beat_risk")
    
    if not circuit.can_execute():
        logger.warning("circuit_breaker_open", provider="l2beat_risk")
        raise httpx.HTTPStatusError(
            "Circuit breaker is open",
            request=httpx.Request("GET", "l2beat/risk"),
            response=httpx.Response(503),
        )
    
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            response = await client.get(
                "https://l2beat.com/api/scaling/risk"
            )
            response.raise_for_status()
            data = response.json()
            
        circuit.record_success()
        
        result: dict[str, dict[str, Any]] = {}
        network_mapping = {
            "arbitrum": "arbitrum-one",
            "optimism": "optimism",
            "base": "base",
            "polygon": "polygon-pos",
        }
        
        for item in data.get("projects", []):
            project_name = item.get("name", "").lower()
            for network_id, l2beat_id in network_mapping.items():
                if l2beat_id in project_name:
                    result[network_id] = {
                        "category": item.get("category", ""),
                        "risk": item.get("risk", {}),
                        "data_availability": item.get("dataAvailability", {}),
                        "upgradeability": item.get("upgradeability", {}),
                    }
                    break
        
        logger.info("l2beat_risk_fetched", networks=len(result))
        return result
        
    except httpx.HTTPStatusError as e:
        circuit.record_failure()
        logger.error("l2beat_risk_http_error", status=e.response.status_code)
        raise
    except httpx.TimeoutException:
        circuit.record_failure()
        logger.error("l2beat_risk_timeout")
        raise
    except Exception as e:
        circuit.record_failure()
        logger.error("l2beat_risk_error", error=str(e))
        raise
