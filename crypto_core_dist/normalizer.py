from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class UnifiedNetworkData:
    network: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tvl: float | None = None
    tvl_change_24h: float | None = None
    gas_usd: float | None = None
    price: float | None = None
    price_change_24h: float | None = None
    market_cap: float | None = None
    volume_24h: float | None = None


DEFILLAMA_MAPPING = {
    "ethereum": "ethereum",
    "solana": "solana",
    "arbitrum": "arbitrum",
    "optimism": "optimism",
    "polygon": "polygon",
    "base": "base",
    "avalanche": "avalanche",
    "bsc": "bsc",
    "bnb chain": "bsc",
    "bnb smart chain": "bsc",
}

COINGECKO_MAPPING = {
    "ethereum": "ethereum",
    "solana": "solana",
    "matic-network": "polygon",
    "arbitrum-one": "arbitrum",
    "base": "base",
    "optimism": "optimism",
    "avalanche-2": "avalanche",
    "binancecoin": "bsc",
}


def map_defillama_to_network(defillama_id: str) -> str | None:
    return DEFILLAMA_MAPPING.get(defillama_id.lower())


async def normalize_tvl_data(tvl_raw: dict[str, Any]) -> dict[str, float]:
    result = {}
    for chain_name, tvl_value in tvl_raw.items():
        network = map_defillama_to_network(chain_name)
        if network:
            result[network] = float(tvl_value)
    return result


async def normalize_price_data(price_raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for coin_id, price_data in price_raw.items():
        network = COINGECKO_MAPPING.get(coin_id)
        if network:
            result[network] = {
                "price": price_data.get("usd"),
                "price_change_24h": price_data.get("usd_24h_change"),
            }
    return result
