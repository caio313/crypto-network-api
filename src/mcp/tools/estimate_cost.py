from pydantic import BaseModel, Field

from src.scoring.dimensions.cost import NETWORK_GAS
from src.scoring.engine import ALLOWED_NETWORKS, validate_network


class EstimateCostInput(BaseModel):
    network: str = Field(..., description="Network ID")
    amount_usd: float = Field(gt=0, description="Amount in USD")
    token: str = Field(min_length=1, max_length=20, description="Token symbol")


class EstimateCostOutput(BaseModel):
    fee_usd: float
    fee_native: float
    fee_percentile: float
    estimated_confirmation_seconds: int


async def estimate_cost(input_data: EstimateCostInput) -> EstimateCostOutput:
    if not validate_network(input_data.network):
        raise ValueError(f"Invalid network: {input_data.network}. Allowed: {ALLOWED_NETWORKS}")
    
    gas_info = NETWORK_GAS.get(input_data.network, {"gas_usd": 0.1, "avg_7d_usd": 0.1, "p90_usd": 0.2})
    
    fee_usd = gas_info.get("gas_usd", 0.1)
    fee_percentile = gas_info.get("p90_usd", fee_usd * 1.5)
    
    default_native: dict[str, float] = {
        "ethereum": 0.002,
        "solana": 0.00001,
        "arbitrum": 0.0001,
        "optimism": 0.00005,
        "polygon": 0.01,
        "base": 0.0001,
        "avalanche": 0.01,
        "bsc": 0.002,
    }
    
    fee_native = default_native.get(input_data.network, 0.001)
    
    finality: dict[str, int] = {
        "ethereum": 900,
        "solana": 5,
        "arbitrum": 60,
        "optimism": 120,
        "polygon": 30,
        "base": 60,
        "avalanche": 2,
        "bsc": 3,
    }
    
    estimated_seconds = finality.get(input_data.network, 60)
    
    return EstimateCostOutput(
        fee_usd=fee_usd,
        fee_native=fee_native,
        fee_percentile=fee_percentile,
        estimated_confirmation_seconds=estimated_seconds,
    )
