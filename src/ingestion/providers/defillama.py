from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import httpx

from src.core.config import settings
from src.core.logging import structlog

logger = structlog.get_logger()


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    name: str
    failure_count: int = 0
    state: CircuitState = CircuitState.CLOSED
    last_failure_time: datetime | None = None

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        if self.failure_count >= settings.circuit_breaker_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                "circuit_breaker_opened",
                provider=self.name,
                failures=self.failure_count,
            )

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN and self.last_failure_time:
            recovery_elapsed = (
                datetime.utcnow() - self.last_failure_time
            ).total_seconds()
            if recovery_elapsed >= settings.circuit_breaker_recovery_seconds:
                self.state = CircuitState.HALF_OPEN
                return True
        return False


_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(provider: str) -> CircuitBreaker:
    if provider not in _circuit_breakers:
        _circuit_breakers[provider] = CircuitBreaker(name=provider)
    return _circuit_breakers[provider]


async def get_tvl_data() -> dict[str, float]:
    circuit = get_circuit_breaker("defillama")
    
    if not circuit.can_execute():
        logger.warning("circuit_breaker_open", provider="defillama")
        raise httpx.HTTPStatusError(
            "Circuit breaker is open",
            request=httpx.Request("GET", "defillama"),
            response=httpx.Response(503),
        )
    
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            response = await client.get(f"{settings.defillama_base_url}/chains")
            response.raise_for_status()
            data = response.json()
            
        circuit.record_success()
        
        tvl_data: dict[str, float] = {}
        chain_mapping = {
            "solana": "Solana",
            "polygon": "Polygon",
            "arbitrum": "Arbitrum",
            "base": "Base",
            "optimism": "Optimism",
            "avalanche": "Avalanche",
            "bsc": "BNB Chain",
            "ethereum": "Ethereum",
        }
        
        for chain in data.get("chains", []):
            chain_name = chain.get("name", "")
            for network_id, display_name in chain_mapping.items():
                if display_name.lower() in chain_name.lower():
                    tvl_data[network_id] = chain.get("tvl", 0.0)
                    break
        
        logger.info("defillama_tvl_fetched", networks=len(tvl_data))
        return tvl_data
        
    except httpx.HTTPStatusError as e:
        circuit.record_failure()
        logger.error("defillama_http_error", status=e.response.status_code)
        raise
    except httpx.TimeoutException:
        circuit.record_failure()
        logger.error("defillama_timeout")
        raise
    except Exception as e:
        circuit.record_failure()
        logger.error("defillama_error", error=str(e))
        raise


async def get_historical_tvl(network: str, days: int = 7) -> list[dict[str, Any]]:
    circuit = get_circuit_breaker(f"defillama_history_{network}")
    
    if not circuit.can_execute():
        raise httpx.HTTPStatusError(
            "Circuit breaker is open",
            request=httpx.Request("GET", f"defillama/{network}"),
            response=httpx.Response(503),
        )
    
    chain_mapping = {
        "solana": "solana",
        "polygon": "polygon",
        "arbitrum": "arbitrum",
        "base": "base",
        "optimism": "optimism",
        "avalanche": "avalanche",
        "bsc": "bsc",
        "ethereum": "ethereum",
    }
    
    defillama_id = chain_mapping.get(network)
    if not defillama_id:
        logger.warning("unknown_network", network=network)
        return []
    
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            response = await client.get(
                f"{settings.defillama_base_url}/history/{defillama_id}",
                params={"days": days},
            )
            response.raise_for_status()
            data = response.json()
            
        circuit.record_success()
        
        historical = []
        for item in data.get("tvl", []):
            historical.append({
                "date": item.get("date"),
                "tvl": item.get("tvl", 0),
            })
        
        logger.info("defillama_history_fetched", network=network, days=len(historical))
        return historical
        
    except httpx.HTTPStatusError as e:
        circuit.record_failure()
        logger.error("defillama_history_http_error", network=network, status=e.response.status_code)
        raise
    except httpx.TimeoutException:
        circuit.record_failure()
        logger.error("defillama_history_timeout", network=network)
        raise
    except Exception as e:
        circuit.record_failure()
        logger.error("defillama_history_error", network=network, error=str(e))
        raise
