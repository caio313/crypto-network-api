from pydantic import BaseModel, Field

from src.models.response import AIFirstResponse
from src.scoring.engine import calculate_all_scores, prioritize_by


class GetBestNetworkInput(BaseModel):
    amount_usd: float = Field(gt=0, description="Amount in USD to send")
    asset: str = Field(min_length=1, max_length=20, description="Asset symbol (e.g., USDC, ETH)")
    priority: str = Field(
        pattern="^(cost|speed|safety|balanced)$", description="Priority for network selection"
    )
    tier: str = Field(default="FREE", description="User's plan tier")


class GetBestNetworkOutput(BaseModel):
    network: str
    score: float
    estimated_fee_usd: float
    estimated_time_seconds: float
    safety_level: str


async def get_best_network(input_data: GetBestNetworkInput) -> AIFirstResponse:
    tier = input_data.tier.upper() if input_data.tier else "FREE"

    if tier == "FREE":
        raise PermissionError(
            '{"error": "plan_required", "required_plan": "PRO", "upgrade_url": "/pricing"}'
        )

    scores = await calculate_all_scores()
    prioritized = prioritize_by(scores, input_data.priority)

    if not prioritized:
        raise ValueError("No networks available for scoring")

    best = prioritized[0]
    alternatives = prioritized[1:3] if len(prioritized) > 1 else []

    warnings = []
    has_alerts = False

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
        action = f"Wait — check alerts for details before sending."
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
        data_freshness_seconds=0,
    )
