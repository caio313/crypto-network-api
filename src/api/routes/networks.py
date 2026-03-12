from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from src.api.deps import CacheDep
from src.core.logging import structlog
from src.models.response import AIFirstResponse
from src.models.score import NetworkScore, NetworkScoresResponse
from src.models.transaction import PriorityLevel
from src.scoring.engine import (
    ALLOWED_NETWORKS,
    calculate_all_scores,
    get_best_network as get_best_network_tool,
    compare_networks,
    validate_network,
    prioritize_by,
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


@router.get("/best")
async def get_best_network_endpoint(
    cache: CacheDep,
    amount_usd: float = Query(..., gt=0, description="Amount in USD"),
    asset: str = Query(..., min_length=1, description="Asset symbol"),
    priority: str = Query("balanced", pattern="^(cost|speed|safety|balanced)$"),
) -> AIFirstResponse:
    if priority not in ["cost", "speed", "safety", "balanced"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Priority must be one of: cost, speed, safety, balanced",
        )

    scores = await calculate_all_scores()
    prioritized = prioritize_by(scores, priority)

    if not prioritized:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No networks available for scoring",
        )

    best = prioritized[0]
    alternatives = prioritized[1:3] if len(prioritized) > 1 else []

    cached = await cache.get_network_scores() if cache else None
    data_freshness = 0
    if cached and cached.get("timestamp"):
        try:
            cached_time = datetime.fromisoformat(cached["timestamp"].replace("Z", "+00:00"))
            data_freshness = int((datetime.now(timezone.utc) - cached_time).total_seconds())
        except Exception:
            data_freshness = 0

    from src.api.routes.alerts import generate_alerts

    alerts = await generate_alerts(cache) if cache else []
    network_alerts = [a for a in alerts if a.get("network") == best.network]
    warnings = [a.get("message", "") for a in network_alerts]
    has_alerts = len(network_alerts) > 0

    safety_level = (
        "high" if best.safety_score >= 70 else "medium" if best.safety_score >= 50 else "low"
    )

    reasoning = (
        f"Selected {best.network.upper()} with overall score {best.score}/100. "
        f"Safety: {best.safety_score}/100, Reliability: {best.reliability_score}/100, "
        f"Cost: {best.cost_score}/100, Speed: {best.speed_score}/100. "
        f"Estimated fee: ${best.gas_usd:.4f}, estimated confirmation time: {best.finality_seconds}s."
    )

    confidence = best.score / 100.0

    if has_alerts:
        action = f"Wait — network has active alerts: {network_alerts[0].get('message', 'Check alerts for details.')}"
    else:
        action = f"Use {best.network.upper()}. Send now."

    alternatives_data = []
    for alt in alternatives:
        alternatives_data.append(
            {
                "network": alt.network,
                "score": alt.score,
                "fee_usd": alt.gas_usd,
            }
        )

    return AIFirstResponse.create(
        success=True,
        data={
            "network": best.network,
            "score": best.score,
            "fee_usd": best.gas_usd,
            "fee_native": best.gas_usd,
            "confirmation_seconds": best.finality_seconds,
            "safety_level": safety_level,
        },
        reasoning=reasoning,
        confidence=confidence,
        action=action,
        warnings=warnings,
        alternatives=alternatives_data,
        data_freshness_seconds=data_freshness,
    )


@router.post("/compare")
async def compare_networks_endpoint(
    networks: list[str],
    amount_usd: float,
    asset: str,
    cache: CacheDep,
) -> AIFirstResponse:
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

    from src.scoring.engine import calculate_network_score

    comparison = []
    for network in networks:
        try:
            score = await calculate_network_score(network)
            safety_level = (
                "high"
                if score.safety_score >= 70
                else "medium"
                if score.safety_score >= 50
                else "low"
            )

            comparison.append(
                {
                    "network": score.network,
                    "score": score.score,
                    "fee_usd": score.gas_usd,
                    "confirmation_seconds": score.finality_seconds,
                    "safety_level": safety_level,
                    "alerts_count": 0,
                }
            )
        except Exception:
            continue

    comparison.sort(key=lambda x: x["score"], reverse=True)

    if not comparison:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No networks could be compared",
        )

    winner = comparison[0]

    reasoning = f"{winner['network'].upper()} scores {winner['score']}/100, higher than all other networks compared. Safety level: {winner['safety_level']}."

    confidence = winner["score"] / 100.0

    data_freshness = 0
    cached = await cache.get_network_scores()
    if cached and cached.get("timestamp"):
        try:
            cached_time = datetime.fromisoformat(cached["timestamp"].replace("Z", "+00:00"))
            data_freshness = int((datetime.now(timezone.utc) - cached_time).total_seconds())
        except Exception:
            data_freshness = 0

    warnings = []

    return AIFirstResponse.create(
        success=True,
        data={
            "comparison": comparison,
        },
        reasoning=reasoning,
        confidence=confidence,
        action=f"Use {winner['network'].upper()} for this transaction.",
        warnings=warnings,
        alternatives=[],
        data_freshness_seconds=data_freshness,
    )
