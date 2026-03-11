from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from src.api.deps import CacheDep, TierDep
from src.api.middleware.auth import get_api_key_tier
from src.core.logging import structlog
from src.scoring.engine import ALLOWED_NETWORKS, validate_network
from src.scoring.dimensions.cost import NETWORK_GAS

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/gas", tags=["gas"])


class GasResponse(BaseModel):
    network: str
    gas_usd: float
    gas_gwei: float | None
    updated_at: str


class GasHistoryResponse(BaseModel):
    network: str
    history: list[dict[str, Any]]
    period_hours: int


DEFAULT_GAS_GWEI: dict[str, float | None] = {
    "ethereum": 20.0,
    "solana": 0.0001,
    "arbitrum": 0.1,
    "optimism": 0.001,
    "polygon": 50.0,
    "base": 0.01,
    "avalanche": 25.0,
    "bsc": 3.0,
}


@router.get("/", response_model=dict[str, GasResponse])
async def list_gas_prices(cache: CacheDep) -> dict[str, GasResponse]:
    cached = await cache.get_gas_prices()
    
    if cached:
        gas_data = cached
    else:
        gas_data = {}
        for network in ALLOWED_NETWORKS:
            gas_info = NETWORK_GAS.get(network, {"gas_usd": 0.1})
            gas_data[network] = {
                "gas_usd": gas_info.get("gas_usd", 0.1),
                "gas_gwei": DEFAULT_GAS_GWEI.get(network),
            }
        await cache.set_gas_prices(gas_data)
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    result = {}
    for network, data in gas_data.items():
        result[network] = GasResponse(
            network=network,
            gas_usd=data.get("gas_usd", 0.1),
            gas_gwei=data.get("gas_gwei"),
            updated_at=timestamp,
        )
    
    return result


@router.get("/{network_id}", response_model=GasResponse)
async def get_gas_price(
    network_id: str,
    cache: CacheDep,
) -> GasResponse:
    if not validate_network(network_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid network. Must be one of: {ALLOWED_NETWORKS}",
        )
    
    cached = await cache.get_gas_prices()
    
    if cached and network_id in cached:
        data = cached[network_id]
    else:
        gas_info = NETWORK_GAS.get(network_id, {"gas_usd": 0.1})
        data = {
            "gas_usd": gas_info.get("gas_usd", 0.1),
            "gas_gwei": DEFAULT_GAS_GWEI.get(network_id),
        }
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    return GasResponse(
        network=network_id,
        gas_usd=data.get("gas_usd", 0.1),
        gas_gwei=data.get("gas_gwei"),
        updated_at=timestamp,
    )


@router.get("/{network_id}/history", response_model=GasHistoryResponse)
async def get_gas_history(
    network_id: str,
    period_hours: int = Query(24, ge=1, le=168),
) -> GasHistoryResponse:
    if not validate_network(network_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid network. Must be one of: {ALLOWED_NETWORKS}",
        )
    
    gas_info = NETWORK_GAS.get(network_id, {"gas_usd": 0.1, "avg_7d_usd": 0.1})
    
    history = []
    base_gas = gas_info.get("gas_usd", 0.1)
    
    for i in range(min(period_hours, 24)):
        history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gas_usd": base_gas * (1 + (i % 10) * 0.01),
        })
    
    return GasHistoryResponse(
        network=network_id,
        history=history,
        period_hours=period_hours,
    )


class GasPredictionResponse(BaseModel):
    network: str
    prediction_1h: float
    prediction_3h: float
    prediction_6h: float
    method: str
    history_points: int
    calculated_at: str


def calculate_sma(values: list[float], window: int) -> float:
    if not values:
        return 0.0
    return sum(values[-window:]) / min(len(values), window)


@router.get("/{network_id}/predict", response_model=GasPredictionResponse)
async def predict_gas_price(
    network_id: str,
    cache: CacheDep,
    tier: TierDep,
) -> GasPredictionResponse:
    if tier not in ("pro", "enterprise"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "plan_required",
                "required_plan": "PRO",
                "upgrade_url": "/pricing",
            },
        )
    
    if not validate_network(network_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid network. Must be one of: {ALLOWED_NETWORKS}",
        )
    
    history_data = await cache.get_gas_history(network_id)
    
    if not history_data or not history_data.get("history"):
        gas_info = NETWORK_GAS.get(network_id, {"gas_usd": 0.1})
        current_gas = gas_info.get("gas_usd", 0.1)
        
        history = []
        for i in range(24, 0, -1):
            ts = datetime.now(timezone.utc) - timedelta(hours=i)
            history.append({
                "timestamp": ts.isoformat(),
                "gas_usd": current_gas * (1 + (i % 10) * 0.01),
            })
        await cache.set_gas_history(network_id, history)
        history_data = {"history": history}
    
    history = history_data.get("history", [])
    gas_values = [h.get("gas_usd", 0) for h in history if "gas_usd" in h]
    
    sma_6 = calculate_sma(gas_values, 6)
    sma_12 = calculate_sma(gas_values, 12)
    sma_24 = calculate_sma(gas_values, 24)
    
    return GasPredictionResponse(
        network=network_id,
        prediction_1h=sma_6,
        prediction_3h=sma_12,
        prediction_6h=sma_24,
        method="simple_moving_average",
        history_points=len(gas_values),
        calculated_at=datetime.now(timezone.utc).isoformat(),
    )
