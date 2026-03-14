from typing import Any

NETWORK_SPEED: dict[str, dict[str, Any]] = {
    "ethereum": {"tps": 30, "confirmation_seconds": 900},
    "solana": {"tps": 65000, "confirmation_seconds": 5},
    "arbitrum": {"tps": 5000, "confirmation_seconds": 60},
    "optimism": {"tps": 4000, "confirmation_seconds": 120},
    "polygon": {"tps": 7000, "confirmation_seconds": 30},
    "base": {"tps": 5000, "confirmation_seconds": 60},
    "avalanche": {"tps": 4500, "confirmation_seconds": 2},
    "bsc": {"tps": 150, "confirmation_seconds": 3},
}


async def calculate_speed_score(network: str) -> float:
    data = NETWORK_SPEED.get(network)
    if not data:
        return 50.0
    tps = data["tps"]
    confirmation = data["confirmation_seconds"]
    if tps >= 10000:
        tps_score = 50.0
    elif tps >= 1000:
        tps_score = 40.0
    elif tps >= 500:
        tps_score = 30.0
    elif tps >= 100:
        tps_score = 20.0
    else:
        tps_score = 10.0
    if confirmation <= 5:
        conf_score = 50.0
    elif confirmation <= 30:
        conf_score = 40.0
    elif confirmation <= 60:
        conf_score = 30.0
    elif confirmation <= 300:
        conf_score = 15.0
    else:
        conf_score = 5.0
    return min(tps_score + conf_score, 100.0)


async def get_speed_metrics(network: str) -> dict[str, Any]:
    score = await calculate_speed_score(network)
    data = NETWORK_SPEED.get(network, {})
    return {
        "score": score,
        "tps": data.get("tps", 0),
        "confirmation_seconds": data.get("confirmation_seconds", 0),
        "network": network,
    }
