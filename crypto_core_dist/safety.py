from typing import Any
from src.ingestion.providers import defillama

NETWORK_TVL: dict[str, float] = {
    "ethereum": 350000000000,
    "solana": 80000000000,
    "arbitrum": 15000000000,
    "optimism": 10000000000,
    "polygon": 5000000000,
    "base": 8000000000,
    "avalanche": 8000000000,
    "bsc": 4000000000,
}


async def calculate_safety_score(network: str, tvl_data: dict[str, float] | None = None) -> float:
    if tvl_data is None:
        tvl_data = NETWORK_TVL
    tvl = tvl_data.get(network, 0.0)
    if tvl <= 0:
        return 0.0
    if tvl >= 10000000000:
        return 100.0
    if tvl >= 1000000000:
        return 85.0
    if tvl >= 500000000:
        return 70.0
    if tvl >= 100000000:
        return 50.0
    if tvl >= 10000000:
        return 30.0
    return 15.0


async def get_safety_metrics(network: str) -> dict[str, Any]:
    try:
        tvl_data = await defillama.get_tvl_data()
    except Exception:
        tvl_data = NETWORK_TVL.copy()
    score = await calculate_safety_score(network, tvl_data)
    tvl = tvl_data.get(network, 0.0)
    return {"score": score, "tvl": tvl, "network": network}
