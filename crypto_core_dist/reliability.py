from typing import Any

NETWORK_RELIABILITY: dict[str, dict[str, Any]] = {
    "ethereum": {"uptime": 99.99, "finality_seconds": 900, "reorg_risk": 0.01},
    "solana": {"uptime": 99.5, "finality_seconds": 5, "reorg_risk": 0.05},
    "arbitrum": {"uptime": 99.9, "finality_seconds": 60, "reorg_risk": 0.02},
    "optimism": {"uptime": 99.9, "finality_seconds": 120, "reorg_risk": 0.02},
    "polygon": {"uptime": 99.8, "finality_seconds": 30, "reorg_risk": 0.03},
    "base": {"uptime": 99.8, "finality_seconds": 60, "reorg_risk": 0.02},
    "avalanche": {"uptime": 99.5, "finality_seconds": 2, "reorg_risk": 0.04},
    "bsc": {"uptime": 99.9, "finality_seconds": 3, "reorg_risk": 0.03},
}


async def calculate_reliability_score(network: str) -> float:
    data = NETWORK_RELIABILITY.get(network)
    if not data:
        return 0.0
    uptime = data["uptime"]
    finality = data["finality_seconds"]
    reorg_risk = data["reorg_risk"]
    uptime_score = min((uptime - 95) / 5, 5) / 5 * 30
    if finality <= 10:
        finality_score = 30.0
    elif finality <= 60:
        finality_score = 25.0
    elif finality <= 300:
        finality_score = 15.0
    else:
        finality_score = 5.0
    reorg_score = (1 - reorg_risk) * 40
    return min(uptime_score + finality_score + reorg_score, 100.0)


async def get_reliability_metrics(network: str) -> dict[str, Any]:
    score = await calculate_reliability_score(network)
    data = NETWORK_RELIABILITY.get(network, {})
    return {
        "score": score,
        "uptime": data.get("uptime", 0),
        "finality_seconds": data.get("finality_seconds", 0),
        "reorg_risk": data.get("reorg_risk", 1),
        "network": network,
    }
