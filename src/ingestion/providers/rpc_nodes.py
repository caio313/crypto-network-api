from typing import Any

import httpx

from src.core.config import settings
from src.core.logging import structlog
from src.ingestion.providers.defillama import (
    get_circuit_breaker,
)

logger = structlog.get_logger()


RPC_CONFIGS: dict[str, str] = {
    "ethereum": "https://eth.llamarpc.com",
    "polygon": "https://polygon.llamarpc.com",
    "arbitrum": "https://arbitrum.llamarpc.com",
    "base": "https://base.llamarpc.com",
    "optimism": "https://optimism.llamarpc.com",
    "avalanche": "https://avalanche.llamarpc.com",
    "bsc": "https://bsc.llamarpc.com",
}


async def get_block_number(network: str) -> int:
    circuit = get_circuit_breaker(f"rpc_{network}")
    
    if not circuit.can_execute():
        logger.warning("circuit_breaker_open", provider=f"rpc_{network}")
        raise httpx.HTTPStatusError(
            "Circuit breaker is open",
            request=httpx.Request("GET", f"rpc_{network}"),
            response=httpx.Response(503),
        )
    
    rpc_url = RPC_CONFIGS.get(network)
    if not rpc_url:
        logger.warning("no_rpc_config", network=network)
        return 0
    
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_blockNumber",
        "params": [],
        "id": 1,
    }
    
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            response = await client.post(
                rpc_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            
        circuit.record_success()
        
        block_number = int(data.get("result", "0x0"), 16)
        logger.info("block_number_fetched", network=network, block=block_number)
        return block_number
        
    except httpx.HTTPStatusError as e:
        circuit.record_failure()
        logger.error("rpc_http_error", network=network, status=e.response.status_code)
        raise
    except httpx.TimeoutException:
        circuit.record_failure()
        logger.error("rpc_timeout", network=network)
        raise
    except Exception as e:
        circuit.record_failure()
        logger.error("rpc_error", network=network, error=str(e))
        raise


async def get_gas_price(network: str) -> dict[str, int]:
    circuit = get_circuit_breaker(f"rpc_gas_{network}")
    
    if not circuit.can_execute():
        logger.warning("circuit_breaker_open", provider=f"rpc_gas_{network}")
        raise httpx.HTTPStatusError(
            "Circuit breaker is open",
            request=httpx.Request("GET", f"rpc_gas_{network}"),
            response=httpx.Response(503),
        )
    
    rpc_url = RPC_CONFIGS.get(network)
    if not rpc_url:
        logger.warning("no_rpc_config", network=network)
        return {"gas_price": 0}
    
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_gasPrice",
        "params": [],
        "id": 1,
    }
    
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            response = await client.post(
                rpc_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            
        circuit.record_success()
        
        gas_price = int(data.get("result", "0x0"), 16)
        logger.info("gas_price_fetched", network=network, gas_price=gas_price)
        return {"gas_price": gas_price}
        
    except httpx.HTTPStatusError as e:
        circuit.record_failure()
        logger.error("rpc_gas_http_error", network=network, status=e.response.status_code)
        raise
    except httpx.TimeoutException:
        circuit.record_failure()
        logger.error("rpc_gas_timeout", network=network)
        raise
    except Exception as e:
        circuit.record_failure()
        logger.error("rpc_gas_error", network=network, error=str(e))
        raise


async def get_latest_block(network: str) -> dict[str, Any]:
    circuit = get_circuit_breaker(f"rpc_block_{network}")
    
    if not circuit.can_execute():
        logger.warning("circuit_breaker_open", provider=f"rpc_block_{network}")
        raise httpx.HTTPStatusError(
            "Circuit breaker is open",
            request=httpx.Request("GET", f"rpc_block_{network}"),
            response=httpx.Response(503),
        )
    
    rpc_url = RPC_CONFIGS.get(network)
    if not rpc_url:
        logger.warning("no_rpc_config", network=network)
        return {}
    
    block_number_payload = {
        "jsonrpc": "2.0",
        "method": "eth_blockNumber",
        "params": [],
        "id": 1,
    }
    
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            block_response = await client.post(
                rpc_url,
                json=block_number_payload,
                headers={"Content-Type": "application/json"},
            )
            block_response.raise_for_status()
            block_data = block_response.json()
            
        block_number = int(block_data.get("result", "0x0"), 16)
        
        block_payload = {
            "jsonrpc": "2.0",
            "method": "eth_getBlockByNumber",
            "params": [hex(block_number), False],
            "id": 1,
        }
        
        block_detail_response = await client.post(
            rpc_url,
            json=block_payload,
            headers={"Content-Type": "application/json"},
        )
        block_detail_response.raise_for_status()
        block_detail = block_detail_response.json()
        
        circuit.record_success()
        
        result: dict[str, Any] = {
            "number": block_number,
            "hash": block_detail.get("result", {}).get("hash", ""),
            "timestamp": int(block_detail.get("result", {}).get("timestamp", "0x0"), 16),
            "gas_limit": int(block_detail.get("result", {}).get("gasLimit", "0x0"), 16),
            "gas_used": int(block_detail.get("result", {}).get("gasUsed", "0x0"), 16),
            "transactions": len(block_detail.get("result", {}).get("transactions", [])),
        }
        
        logger.info("latest_block_fetched", network=network, block=block_number)
        return result
        
    except httpx.HTTPStatusError as e:
        circuit.record_failure()
        logger.error("rpc_block_http_error", network=network, status=e.response.status_code)
        raise
    except httpx.TimeoutException:
        circuit.record_failure()
        logger.error("rpc_block_timeout", network=network)
        raise
    except Exception as e:
        circuit.record_failure()
        logger.error("rpc_block_error", network=network, error=str(e))
        raise
