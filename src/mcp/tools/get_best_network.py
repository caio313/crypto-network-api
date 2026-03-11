from pydantic import BaseModel, Field

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
    reasoning: str


async def get_best_network(input_data: GetBestNetworkInput) -> GetBestNetworkOutput:
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

    reasoning = (
        f"Selected {best.network.upper()} with overall score {best.score}/100. "
        f"Safety: {best.safety_score}/100, Reliability: {best.reliability_score}/100, "
        f"Cost: {best.cost_score}/100, Speed: {best.speed_score}/100. "
        f"Estimated fee: ${best.gas_usd:.4f}, estimated confirmation time: {best.finality_seconds}s."
    )

    return GetBestNetworkOutput(
        network=best.network,
        score=best.score,
        estimated_fee_usd=best.gas_usd,
        estimated_time_seconds=best.finality_seconds,
        reasoning=reasoning,
    )
