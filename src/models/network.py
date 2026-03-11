from enum import Enum
from pydantic import BaseModel, Field


class NetworkId(str, Enum):
    SOLANA = "solana"
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"
    BASE = "base"
    OPTIMISM = "optimism"
    AVALANCHE = "avalanche"
    BSC = "bsc"
    ETHEREUM = "ethereum"


class NetworkCategory(str, Enum):
    L1 = "L1"
    L2 = "L2"
    SIDECHAIN = "Sidechain"


class Network(BaseModel):
    id: NetworkId
    name: str
    category: NetworkCategory
    chain_id: int | None = None
    rpc_url: str | None = None
    explorer_url: str | None = None
    native_token: str
    coingecko_id: str
    defillama_id: str


NETWORKS: dict[NetworkId, Network] = {
    NetworkId.SOLANA: Network(
        id=NetworkId.SOLANA,
        name="Solana",
        category=NetworkCategory.L1,
        chain_id=101,
        rpc_url="https://api.mainnet-beta.solana.com",
        explorer_url="https://explorer.solana.com",
        native_token="SOL",
        coingecko_id="solana",
        defillama_id="solana",
    ),
    NetworkId.POLYGON: Network(
        id=NetworkId.POLYGON,
        name="Polygon PoS",
        category=NetworkCategory.SIDECHAIN,
        chain_id=137,
        rpc_url="https://polygon-rpc.com",
        explorer_url="https://polygonscan.com",
        native_token="MATIC",
        coingecko_id="matic-network",
        defillama_id="polygon",
    ),
    NetworkId.ARBITRUM: Network(
        id=NetworkId.ARBITRUM,
        name="Arbitrum One",
        category=NetworkCategory.L2,
        chain_id=42161,
        rpc_url="https://arb1.arbitrum.io/rpc",
        explorer_url="https://arbiscan.io",
        native_token="ETH",
        coingecko_id="arbitrum-one",
        defillama_id="arbitrum",
    ),
    NetworkId.BASE: Network(
        id=NetworkId.BASE,
        name="Base",
        category=NetworkCategory.L2,
        chain_id=8453,
        rpc_url="https://mainnet.base.org",
        explorer_url="https://basescan.org",
        native_token="ETH",
        coingecko_id="base",
        defillama_id="base",
    ),
    NetworkId.OPTIMISM: Network(
        id=NetworkId.OPTIMISM,
        name="Optimism",
        category=NetworkCategory.L2,
        chain_id=10,
        rpc_url="https://mainnet.optimism.io",
        explorer_url="https://optimistic.etherscan.io",
        native_token="ETH",
        coingecko_id="optimism",
        defillama_id="optimism",
    ),
    NetworkId.AVALANCHE: Network(
        id=NetworkId.AVALANCHE,
        name="Avalanche C-Chain",
        category=NetworkCategory.L1,
        chain_id=43114,
        rpc_url="https://api.avax.network/ext/bc/C/rpc",
        explorer_url="https://snowtrace.io",
        native_token="AVAX",
        coingecko_id="avalanche-2",
        defillama_id="avalanche",
    ),
    NetworkId.BSC: Network(
        id=NetworkId.BSC,
        name="BNB Smart Chain",
        category=NetworkCategory.L1,
        chain_id=56,
        rpc_url="https://bsc-dataseed.binance.org",
        explorer_url="https://bscscan.com",
        native_token="BNB",
        coingecko_id="binancecoin",
        defillama_id="bsc",
    ),
    NetworkId.ETHEREUM: Network(
        id=NetworkId.ETHEREUM,
        name="Ethereum",
        category=NetworkCategory.L1,
        chain_id=1,
        rpc_url="https://eth.llamarpc.com",
        explorer_url="https://etherscan.io",
        native_token="ETH",
        coingecko_id="ethereum",
        defillama_id="ethereum",
    ),
}


def get_network(network_id: str) -> Network | None:
    try:
        return NETWORKS[NetworkId(network_id)]
    except ValueError:
        return None


def get_all_networks() -> list[Network]:
    return list(NETWORKS.values())
