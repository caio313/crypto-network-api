from datetime import datetime, timezone
from typing import Any

from src.core.logging import structlog
from src.models.score import NetworkScore, ScoreInput
from src.scoring.dimensions import cost, reliability, safety, speed
from src.scoring.weights import DEFAULT_WEIGHTS, ScoreWeights

logger = structlog.get_logger()

ALLOWED_NETWORKS: frozenset[str] = frozenset({
    "solana",
    "polygon",
    "arbitrum",
    "base",
    "optimism",
    "avalanche",
    "bsc",
    "ethereum",
})


def validate_network(network: str) -> bool:
    return network in ALLOWED_NETWORKS


def validate_networks(networks: list[str]) -> bool:
    return all(n in ALLOWED_NETWORKS for n in networks)


def calculate_final_score(
    safety_score: float,
    reliability_score: float,
    cost_score: float,
    speed_score: float,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> float:
    score = (
        safety_score * weights.safety
        + reliability_score * weights.reliability
        + cost_score * weights.cost
        + speed_score * weights.speed
    )
    return round(score, 2)


async def calculate_network_score(network: str) -> NetworkScore:
    if not validate_network(network):
        raise ValueError(f"Invalid network: {network}. Must be one of {ALLOWED_NETWORKS}")
    
    safety_metrics = await safety.get_safety_metrics(network)
    reliability_metrics = await reliability.get_reliability_metrics(network)
    cost_metrics = await cost.get_cost_metrics(network)
    speed_metrics = await speed.get_speed_metrics(network)
    
    final_score = calculate_final_score(
        safety_score=safety_metrics["score"],
        reliability_score=reliability_metrics["score"],
        cost_score=cost_metrics["score"],
        speed_score=speed_metrics["score"],
    )
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    return NetworkScore(
        network=network,
        score=final_score,
        safety_score=safety_metrics["score"],
        reliability_score=reliability_metrics["score"],
        cost_score=cost_metrics["score"],
        speed_score=speed_metrics["score"],
        tvl=safety_metrics.get("tvl", 0.0),
        gas_usd=cost_metrics.get("gas_usd", 0.0),
        tps=speed_metrics.get("tps", 0.0),
        finality_seconds=reliability_metrics.get("finality_seconds", 0.0),
        timestamp=timestamp,
    )


async def calculate_all_scores() -> list[NetworkScore]:
    scores: list[NetworkScore] = []
    for network in ALLOWED_NETWORKS:
        try:
            score = await calculate_network_score(network)
            scores.append(score)
        except Exception as e:
            logger.error("score_calculation_failed", network=network, error=str(e))
            continue
    
    logger.info("scores_calculated", count=len(scores))
    return scores


def prioritize_by(
    scores: list[NetworkScore],
    priority: str,
) -> list[NetworkScore]:
    match priority:
        case "cost":
            return sorted(scores, key=lambda s: s.cost_score, reverse=True)
        case "speed":
            return sorted(scores, key=lambda s: s.speed_score, reverse=True)
        case "safety":
            return sorted(scores, key=lambda s: s.safety_score, reverse=True)
        case _:
            return sorted(scores, key=lambda s: s.score, reverse=True)


async def get_best_network(input_data: ScoreInput) -> dict[str, Any]:
    scores = await calculate_all_scores()
    prioritized = prioritize_by(scores, input_data.priority)
    
    if not prioritized:
        raise ValueError("No networks available for scoring")
    
    best = prioritized[0]
    
    reasoning = (
        f"Selected {best.network.upper()} with overall score {best.score}/100 "
        f"(safety: {best.safety_score}, reliability: {best.reliability_score}, "
        f"cost: {best.cost_score}, speed: {best.speed_score}). "
        f"Estimated fee: ${best.gas_usd:.4f}, "
        f"estimated confirmation: {best.finality_seconds}s."
    )
    
    return {
        "network": best.network,
        "score": best.score,
        "estimated_fee_usd": best.gas_usd,
        "estimated_time_seconds": best.finality_seconds,
        "reasoning": reasoning,
    }


async def compare_networks(
    networks: list[str],
    amount_usd: float,
    asset: str,
) -> dict[str, Any]:
    invalid = [n for n in networks if not validate_network(n)]
    if invalid:
        raise ValueError(f"Invalid networks: {invalid}. Must be from {ALLOWED_NETWORKS}")
    
    scores = []
    for network in networks:
        try:
            score = await calculate_network_score(network)
            scores.append({
                "network": score.network,
                "score": score.score,
                "fee_usd": score.gas_usd,
                "time_s": score.finality_seconds,
                "safety_level": "high" if score.safety_score >= 70 else "medium" if score.safety_score >= 50 else "low",
            })
        except Exception as e:
            logger.error("compare_networks_error", network=network, error=str(e))
            continue
    
    return {"comparison_table": scores}
