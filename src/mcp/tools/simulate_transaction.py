from pydantic import BaseModel, Field

from src.scoring.dimensions.cost import NETWORK_GAS
from src.scoring.engine import ALLOWED_NETWORKS, validate_network


class SimulateTransactionInput(BaseModel):
    from_network: str = Field(..., min_length=1, description="Source network ID")
    to_network: str = Field(..., min_length=1, description="Destination network ID")
    amount_usd: float = Field(gt=0, description="Amount in USD")
    asset: str = Field(min_length=1, max_length=20, description="Asset symbol")
    tier: str = Field(default="FREE", description="User's plan tier")


class SimulateTransactionOutput(BaseModel):
    steps: list[str]
    total_fee_usd: float
    total_time_seconds: int
    bridge_used: str | None
    risks: list[str]


FREE_NETWORKS = frozenset({"ethereum", "polygon", "arbitrum", "solana"})


def validate_network_for_tier(network: str, tier: str) -> bool:
    if tier.upper() in {"PRO", "ENTERPRISE"}:
        return validate_network(network)
    return network in FREE_NETWORKS


async def simulate_transaction(input_data: SimulateTransactionInput) -> SimulateTransactionOutput:
    tier = input_data.tier.upper() if input_data.tier else "FREE"
    
    if not validate_network_for_tier(input_data.from_network, tier):
        raise ValueError(
            f"Network {input_data.from_network} not available in {tier} plan"
        )
    
    if not validate_network_for_tier(input_data.to_network, tier):
        raise ValueError(
            f"Network {input_data.to_network} not available in {tier} plan"
        )
    
    if tier == "FREE":
        raise PermissionError(
            '{"error": "plan_required", "required_plan": "PRO", "upgrade_url": "/pricing"}'
        )
        raise ValueError(
            f"Network {input_data.to_network} not available in {tier} plan"
        )
    
    from_gas = NETWORK_GAS.get(input_data.from_network, {"gas_usd": 0.1})
    to_gas = NETWORK_GAS.get(input_data.to_network, {"gas_usd": 0.1})
    
    bridge_fee = input_data.amount_usd * 0.003
    
    total_fee = from_gas.get("gas_usd", 0.1) + to_gas.get("gas_usd", 0.1) + bridge_fee
    
    steps = [
        f"1. Initiate transfer of {input_data.amount_usd} {input_data.asset} on {input_data.from_network}",
        f"2. Approve token for bridge (if not already approved)",
        f"3. Bridge to {input_data.to_network} via Cross-chain Bridge",
        f"4. Wait for confirmation on destination network",
        f"5. Receive {input_data.amount_usd - bridge_fee:.2f} {input_data.asset} on {input_data.to_network}",
    ]
    
    bridge_used = "Cross-chain Bridge"
    
    risks = [
        "Bridge smart contract risk",
        "Potential delays during network congestion",
        "Slippage tolerance recommended (0.5%)",
        "Cross-chain bridge exploits (rare but possible)",
    ]
    
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
    
    total_time = finality.get(input_data.from_network, 60) + finality.get(input_data.to_network, 60)
    
    return SimulateTransactionOutput(
        steps=steps,
        total_fee_usd=round(total_fee, 4),
        total_time_seconds=total_time,
        bridge_used=bridge_used,
        risks=risks,
    )
