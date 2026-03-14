from typing import Any

NETWORK_GAS: dict[str, dict[str, Any]] = {
    "ethereum": {"gas_usd": 5.0, "avg_7d_usd": 4.5, "p90_usd": 8.0},
    "solana": {"gas_usd": 0.001, "avg_7d_usd": 0.001, "p90_usd": 0.005},
    "arbitrum": {"gas_usd": 0.1, "avg_7d_usd": 0.08, "p90_usd": 0.2},
    "optimism": {"gas_usd": 0.05, "avg_7d_usd": 0.04, "p90_usd": 0.1},
    "polygon": {"gas_usd": 0.01, "avg_7d_usd": 0.01, "p90_usd": 0.05},
    "base": {"gas_usd": 0.05, "avg_7d_usd": 0.04, "p90_usd": 0.1},
    "avalanche": {"gas_usd": 0.02, "avg_7d_usd": 0.02, "p90_usd": 0.05},
    "bsc": {"gas_usd": 0.005, "avg_7d_usd": 0.005, "p90_usd": 0.01},
}


async def calculate_cost_score(network: str) -> float:
    data = NETWORK_GAS.get(network)
    if not data:
        return 50.0
    gas = data["gas_usd"]
    if gas <= 0.01:
        return 100.0
    if gas <= 0.1:
        return 80.0
    if gas <= 0.5:
        return 60.0
    if gas <= 1.0:
        return 40.0
    if gas <= 5.0:
        return 20.0
    return 5.0


async def get_cost_metrics(network: str) -> dict[str, Any]:
    score = await calculate_cost_score(network)
    data = NETWORK_GAS.get(network, {})
    return {
        "score": score,
        "gas_usd": data.get("gas_usd", 0),
        "avg_7d_usd": data.get("avg_7d_usd", 0),
        "p90_usd": data.get("p90_usd", 0),
        "network": network,
    }
