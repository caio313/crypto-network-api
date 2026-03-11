from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from src.api.deps import CacheDep
from src.core.logging import structlog
from src.models.score import NetworkScore, NetworkScoresResponse
from src.models.transaction import PriorityLevel
from src.scoring.engine import (
    ALLOWED_NETWORKS,
    calculate_all_scores,
    get_best_network,
    compare_networks,
    validate_network,
)
from src.scoring.weights import DEFAULT_WEIGHTS

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/networks", tags=["networks"])


@router.get("/", response_model=NetworkScoresResponse)
async def list_networks(
    cache: CacheDep,
    priority: str | None = Query(
        None,
        pattern="^(cost|speed|safety|balanced)$",
    ),
) -> NetworkScoresResponse:
    cached = await cache.get_network_scores()
    
    if cached:
        scores = [NetworkScore(**s) for s in cached.get("scores", [])]
    else:
        scores = await calculate_all_scores()
        scores_data = [s.model_dump() for s in scores]
        await cache.set_network_scores({"scores": scores_data})
    
    if priority:
        from src.scoring.engine import prioritize_by
        
        class PriorityInput:
            def __init__(self, amount_usd: float, asset: str, priority: str):
                self.amount_usd = amount_usd
                self.asset = asset
                self.priority = priority
        
        input_obj = PriorityInput(amount_usd=100, asset="USDC", priority=priority)
        scores = prioritize_by(scores, priority)
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    return NetworkScoresResponse(scores=scores, timestamp=timestamp)


@router.get("/{network_id}", response_model=NetworkScore)
async def get_network(
    network_id: str,
    cache: CacheDep,
) -> NetworkScore:
    if not validate_network(network_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid network. Must be one of: {ALLOWED_NETWORKS}",
        )
    
    cached = await cache.get_network_scores()
    
    if cached:
        for s in cached.get("scores", []):
            if s.get("network") == network_id:
                return NetworkScore(**s)
    
    scores = await calculate_all_scores()
    
    for score in scores:
        if score.network == network_id:
            return score
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Network {network_id} not found",
    )


@router.post("/best")
async def get_best_network_endpoint(
    amount_usd: float,
    asset: str,
    priority: str = "balanced",
) -> dict[str, Any]:
    if priority not in ["cost", "speed", "safety", "balanced"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Priority must be one of: cost, speed, safety, balanced",
        )
    
    from src.models.score import ScoreInput
    
    input_data = ScoreInput(
        amount_usd=amount_usd,
        asset=asset,
        priority=priority,
    )
    
    result = await get_best_network(input_data)
    return result


@router.post("/compare")
async def compare_networks_endpoint(
    networks: list[str],
    amount_usd: float,
    asset: str,
) -> dict[str, Any]:
    if not networks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Networks list cannot be empty",
        )
    
    invalid = [n for n in networks if not validate_network(n)]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid networks: {invalid}. Must be from {ALLOWED_NETWORKS}",
        )
    
    result = await compare_networks(networks, amount_usd, asset)
    return result
