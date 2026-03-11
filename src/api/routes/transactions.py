from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel, Field

from src.api.deps import CacheDep
from src.core.logging import structlog
from src.scoring.engine import ALLOWED_NETWORKS, validate_network

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/transactions", tags=["transactions"])

FREE_NETWORKS: frozenset[str] = frozenset({
    "ethereum",
    "polygon",
    "arbitrum",
    "solana",
})

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


@router.post("/estimate", response_model=EstimateResponse)
async def estimate_transaction(
    request: EstimateRequest,
    response: Response,
    x_plan_tier: str = Header("FREE", alias="X-Plan-Tier"),
) -> EstimateResponse:
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
    
    fee_usd = 0.1
    fee_native = 0.001
    estimated_seconds = 30
    
    default_gas: dict[str, float] = {
        "ethereum": 5.0,
        "solana": 0.001,
        "arbitrum": 0.1,
        "optimism": 0.05,
        "polygon": 0.01,
        "base": 0.05,
        "avalanche": 0.02,
        "bsc": 0.005,
    }
    
    fee_usd = default_gas.get(request.from_network, 0.1)
    
    return EstimateResponse(
        fee_usd=fee_usd,
        fee_native=fee_native,
        fee_percentile=fee_usd * 1.2,
        estimated_confirmation_seconds=estimated_seconds,
        from_network=request.from_network,
        to_network=request.to_network,
        amount_usd=request.amount_usd,
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
