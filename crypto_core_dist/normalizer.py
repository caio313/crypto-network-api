import asyncio
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from src.cache import ttl as ttl_constants
from src.core.logging import structlog
from src.ingestion.providers import coingecko, defillama
from src.models.network import NetworkId

logger = structlog.get_logger()


@dataclass
class UnifiedNetworkData:
    """Unified data structure for network metrics."""

    network: NetworkId
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tvl_usd: float | None = None
    price_usd: float | None = None
    market_cap_usd: float | None = None
    volume_24h_usd: float | None = None
    circulating_supply: float | None = None
    gas_price_gwei: float | None = None
    gas_price_usd: float | None = None
    avg_block_time_seconds: float | None = None
    daily_transactions: int | None = None
    daily_active_addresses: int | None = None
    hash_rate: float | None = None
    staking_ratio: float | None = None
    validator_count: int | None = None
    nakamoto_coefficient: int | None = None
    client_diversity: float | None = None
    development_activity: float | None = None
    uptime_24h: float | None = None
    uptime_7d: float | None = None
    finality_time_seconds: float | None = None
    reorg_count_7d: int | None = None
    tps: float | None = None
    confirmation_time_minutes: float | None = None
    transaction_fee_usd: float | None = None
    avg_transaction_fee_7d_usd: float | None = None
    p90_transaction_fee_usd: float | None = None


async def map_defillama_to_network(defillama_id: str) -> NetworkId | None:
    """Map DefiLlama chain ID to our NetworkId enum."""
    mapping = {
        "Ethereum": NetworkId.ETHEREUM,
        "Solana": NetworkId.SOLANA,
        "Arbitrum": NetworkId.ARBITRUM,
        "Optimism": NetworkId.OPTIMISM,
        "Polygon": NetworkId.POLYGON,
        "Base": NetworkId.BASE,
        "Avalanche": NetworkId.AVALANCHE,
        "BSC": NetworkId.BSC,
    }
    return mapping.get(defillama_id)


async def normalize_tvl_data(tvl_raw: dict[str, Any]) -> UnifiedNetworkData | None:
    """Normalize TVL data from DefiLlama."""
    try:
        chain_name = tvl_raw.get("gecko_id", "").capitalize()
        if not chain_name:
            return None

        network_id = await map_defillama_to_network(chain_name)
        if not network_id:
            return None

        return UnifiedNetworkData(
            network=network_id,
            tvl_usd=float(tvl_raw.get("tvl", 0)),
            timestamp=datetime.utcnow(),
        )
    except Exception as e:
        logger.warning("Failed to normalize TVL data", error=str(e), data=tvl_raw)
        return None


async def normalize_price_data(price_raw: dict[str, Any]) -> UnifiedNetworkData | None:
    """Normalize price data from CoinGecko."""
    try:
        coin_id = price_raw.get("id", "")
        network_mapping = {
            "ethereum": NetworkId.ETHEREUM,
            "solana": NetworkId.SOLANA,
            "arbitrum": NetworkId.ARBITRUM,
            "optimism": NetworkId.OPTIMISM,
            "polygon": NetworkId.POLYGON,
            "base": NetworkId.BASE,
            "avalanche": NetworkId.AVALANCHE,
            "binancecoin": NetworkId.BSC,
        }

        network_id = network_mapping.get(coin_id)
        if not network_id:
            return None

        return UnifiedNetworkData(
            network=network_id,
            price_usd=float(price_raw.get("current_price", 0)),
            market_cap_usd=float(price_raw.get("market_cap", 0)),
            volume_24h_usd=float(price_raw.get("total_volume", 0)),
            circulating_supply=float(price_raw.get("circulating_supply", 0)),
            timestamp=datetime.utcnow(),
        )
    except Exception as e:
        logger.warning("Failed to normalize price data", error=str(e), data=price_raw)
        return None
