from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel, Field

from src.api.deps import CacheDep
from src.core.logging import structlog
from src.models.response import AIFirstResponse
from src.scoring.dimensions.cost import NETWORK_GAS
from src.scoring.engine import ALLOWED_NETWORKS, validate_network

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/transactions", tags=["transactions"])

FREE_NETWORKS: frozenset[str] = frozenset(
    {
        "ethereum",
        "polygon",
        "arbitrum",
        "solana",
    }
)

ALLOWED_TIERS: frozenset[str] = frozenset({"FREE", "PRO", "ENTERPRISE"})


def validate_network_for_tier(network: str, tier: str) -> bool:
    if tier in {"PRO", "ENTERPRISE"}:
        return validate_network(network)
    return network in FREE_NETWORKS


class EstimateRequest(BaseModel):
    from_network: str = Field(..., min_length=1)
    to_network: str = Field(..., min_length=1)
    amount_usd: float = Field(gt=0)
    token: str = Field(min_length=1, max_length=20)


class EstimateResponse(BaseModel):
    fee_usd: float
    fee_native: float
    fee_percentile: float
    estimated_confirmation_seconds: int
    from_network: str
    to_network: str
    amount_usd: float


class SimulateRequest(BaseModel):
    from_network: str = Field(..., min_length=1)
    to_network: str = Field(..., min_length=1)
    amount_usd: float = Field(gt=0)
    asset: str = Field(min_length=1, max_length=20)


class SimulateResponse(BaseModel):
    steps: list[str]
    total_fee_usd: float
    total_time_seconds: int
    bridge_used: str | None
    risks: list[str]
    from_network: str
    to_network: str
    amount_usd: float


class UsageResponse(BaseModel):
    requests_used: int
    requests_limit: int
    percent_used: float
    reset_date: str
    tier: str


MOCK_USAGE: dict[str, dict[str, Any]] = {
    "FREE": {"requests_used": 2500, "requests_limit": 10000},
    "PRO": {"requests_used": 125000, "requests_limit": 500000},
    "ENTERPRISE": {"requests_used": 50000, "requests_limit": 999999999},
}


def check_plan_tier(tier: str) -> str:
    if tier not in ALLOWED_TIERS:
        return "FREE"
    return tier


@router.post("/estimate")
async def estimate_transaction(
    request: EstimateRequest,
    response: Response,
    cache: CacheDep,
    x_plan_tier: str = Header("FREE", alias="X-Plan-Tier"),
) -> AIFirstResponse:
    tier = check_plan_tier(x_plan_tier)

    if not validate_network_for_tier(request.from_network, tier):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "plan_required",
                "required_plan": "PRO",
                "upgrade_url": "/pricing",
                "message": f"Network {request.from_network} not available in {tier} plan",
            },
        )

    if not validate_network_for_tier(request.to_network, tier):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "plan_required",
                "required_plan": "PRO",
                "upgrade_url": "/pricing",
                "message": f"Network {request.to_network} not available in {tier} plan",
            },
        )

    response.headers["X-Plan-Tier"] = tier

    gas_info = NETWORK_GAS.get(
        request.from_network, {"gas_usd": 0.1, "avg_7d_usd": 0.1, "p90_usd": 0.2}
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

    fee_native = default_native.get(request.from_network, 0.001)

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

    estimated_seconds = finality.get(request.from_network, 60)

    data_freshness = 0
    if cache:
        cached = await cache.get_network_scores()
        if cached and cached.get("timestamp"):
            try:
                cached_time = datetime.fromisoformat(cached["timestamp"].replace("Z", "+00:00"))
                data_freshness = int((datetime.now(timezone.utc) - cached_time).total_seconds())
            except Exception:
                data_freshness = 0

    if data_freshness < 30:
        confidence = 0.95
    elif data_freshness < 120:
        confidence = 0.75
    else:
        confidence = 0.50

    gas_trend = "stable"
    if fee_usd > avg_7d * 1.2:
        gas_trend = "increasing"
    elif fee_usd < avg_7d * 0.8:
        gas_trend = "decreasing"

    fee_ratio = fee_usd / avg_7d if avg_7d > 0 else 1.0
    if fee_ratio < 0.75:
        reasoning = f"Current fee ${fee_usd:.4f} is {((1 - fee_ratio) * 100):.0f}% below 7-day average ${avg_7d:.4f}. This is a favorable time to transact."
    elif fee_ratio <= 1.0:
        reasoning = f"Current fee ${fee_usd:.4f} is within normal range (7-day avg: ${avg_7d:.4f}). Proceed with transaction."
    else:
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

    return AIFirstResponse.create(
        success=True,
        data={
            "network": request.from_network,
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
        data_freshness_seconds=data_freshness,
    )


@router.post("/simulate", response_model=SimulateResponse)
async def simulate_transaction(
    request: SimulateRequest,
    response: Response,
    x_plan_tier: str = Header("FREE", alias="X-Plan-Tier"),
) -> SimulateResponse:
    tier = check_plan_tier(x_plan_tier)

    if tier == "FREE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "plan_required",
                "required_plan": "PRO",
                "upgrade_url": "/pricing",
            },
        )

    if not validate_network_for_tier(request.from_network, tier):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "plan_required",
                "required_plan": "PRO",
                "upgrade_url": "/pricing",
                "message": f"Network {request.from_network} not available in {tier} plan",
            },
        )

    if not validate_network_for_tier(request.to_network, tier):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "plan_required",
                "required_plan": "PRO",
                "upgrade_url": "/pricing",
                "message": f"Network {request.to_network} not available in {tier} plan",
            },
        )

    response.headers["X-Plan-Tier"] = tier

    steps = [
        f"1. Initiate transfer of {request.amount_usd} {request.asset} on {request.from_network}",
        f"2. Bridge to {request.to_network} via generic bridge",
        f"3. Confirm transaction on {request.to_network}",
    ]

    total_fee = 0.5
    bridge_used = "Generic Bridge"
    risks = ["Bridge failure risk", "Slippage tolerance", "Network congestion"]

    return SimulateResponse(
        steps=steps,
        total_fee_usd=total_fee,
        total_time_seconds=180,
        bridge_used=bridge_used,
        risks=risks,
        from_network=request.from_network,
        to_network=request.to_network,
        amount_usd=request.amount_usd,
    )


router_account = APIRouter(prefix="/v1/account", tags=["account"])


@router_account.get("/usage", response_model=UsageResponse)
async def get_account_usage(
    response: Response,
    x_plan_tier: str = Header("FREE", alias="X-Plan-Tier"),
) -> UsageResponse:
    tier = check_plan_tier(x_plan_tier)

    usage_data = MOCK_USAGE.get(tier, MOCK_USAGE["FREE"])
    requests_used = usage_data["requests_used"]
    requests_limit = usage_data["requests_limit"]

    percent_used = (requests_used / requests_limit * 100) if requests_limit > 0 else 0

    now = datetime.now(timezone.utc)
    if now.month == 12:
        next_month = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    reset_date = next_month.strftime("%Y-%m-%dT00:00:00Z")

    response.headers["X-Plan-Tier"] = tier

    return UsageResponse(
        requests_used=requests_used,
        requests_limit=requests_limit,
        percent_used=round(percent_used, 2),
        reset_date=reset_date,
        tier=tier,
    )
