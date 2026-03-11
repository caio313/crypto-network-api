from pydantic import BaseModel, Field, field_validator

from src.scoring.engine import ALLOWED_NETWORKS, calculate_network_score


class CompareNetworksInput(BaseModel):
    networks: list[str] = Field(
        ..., min_length=2, max_length=8, description="List of network IDs to compare"
    )
    amount_usd: float = Field(gt=0, description="Amount in USD")
    asset: str = Field(min_length=1, max_length=20, description="Asset symbol")
    tier: str = Field(default="FREE", description="User's plan tier")

    @field_validator("networks")
    @classmethod
    def validate_networks(cls, v):
        for network in v:
            if network not in ALLOWED_NETWORKS:
                raise ValueError(f"Invalid network: {network}. Allowed: {list(ALLOWED_NETWORKS)}")
        return v


class NetworkComparisonItem(BaseModel):
    network: str
    score: float
    fee_usd: float
    time_s: float
    safety_level: str


class CompareNetworksOutput(BaseModel):
    comparison_table: list[NetworkComparisonItem]


async def compare_networks(input_data: CompareNetworksInput) -> CompareNetworksOutput:
    tier = input_data.tier.upper() if input_data.tier else "FREE"

    if tier == "FREE":
        raise PermissionError(
            '{"error": "plan_required", "required_plan": "PRO", "upgrade_url": "/pricing"}'
        )

    invalid = [n for n in input_data.networks if n not in ALLOWED_NETWORKS]
    if invalid:
        raise ValueError(f"Invalid networks: {invalid}. Allowed: {ALLOWED_NETWORKS}")

    comparison = []
    for network in input_data.networks:
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
                NetworkComparisonItem(
                    network=score.network,
                    score=score.score,
                    fee_usd=score.gas_usd,
                    time_s=score.finality_seconds,
                    safety_level=safety_level,
                )
            )
        except Exception:
            continue

    comparison.sort(key=lambda x: x.score, reverse=True)

    return CompareNetworksOutput(comparison_table=comparison)
