from pydantic import BaseModel, Field

from src.models.response import AIFirstResponse
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


async def estimate_cost(input_data: EstimateCostInput) -> AIFirstResponse:
    if not validate_network(input_data.network):
        raise ValueError(f"Invalid network: {input_data.network}. Allowed: {ALLOWED_NETWORKS}")

    gas_info = NETWORK_GAS.get(
        input_data.network, {"gas_usd": 0.1, "avg_7d_usd": 0.1, "p90_usd": 0.2}
    )

    fee_usd = gas_info.get("gas_usd", 0.1)
    avg_7d = gas_info.get("avg_7d_usd", fee_usd)
    p75 = fee_usd * 1.25
    p90 = gas_info.get("p90_usd", fee_usd * 1.5)

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

    gas_trend = "stable"
    if fee_usd > avg_7d * 1.2:
        gas_trend = "increasing"
    elif fee_usd < avg_7d * 0.8:
        gas_trend = "decreasing"

    fee_ratio = fee_usd / avg_7d if avg_7d > 0 else 1.0
    if fee_ratio < 0.75:
        fee_status = "favorable"
        reasoning = f"Current fee ${fee_usd:.4f} is {((1 - fee_ratio) * 100):.0f}% below 7-day average ${avg_7d:.4f}. This is a favorable time to transact."
    elif fee_ratio <= 1.0:
        fee_status = "normal"
        reasoning = f"Current fee ${fee_usd:.4f} is within normal range (7-day avg: ${avg_7d:.4f}). Proceed with transaction."
    else:
        fee_status = "high"
        reasoning = f"Current fee ${fee_usd:.4f} is {((fee_ratio - 1) * 100):.0f}% above 7-day average ${avg_7d:.4f}. Consider waiting for lower fees."

    warnings = []
    if fee_usd > p90:
        warnings = ["critical_fee"]
    elif fee_usd > p75:
        warnings = ["high_fee"]

    if fee_usd > p75:
        action = (
            f"Wait. Fee is above average. Consider waiting {int((fee_ratio - 1) * 60)} minutes."
        )
    else:
        action = "Proceed with transaction. Fee is favorable."

    confidence = 0.95

    return AIFirstResponse.create(
        success=True,
        data={
            "network": input_data.network,
            "fee_usd": fee_usd,
            "fee_native": fee_native,
            "fee_percentile": p90,
            "confirmation_seconds": estimated_seconds,
            "gas_trend": gas_trend,
        },
        reasoning=reasoning,
        confidence=confidence,
        action=action,
        warnings=warnings,
        alternatives=[],
        data_freshness_seconds=0,
    )

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
