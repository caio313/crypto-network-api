import pytest

from src.ingestion.normalizer import (
    normalize_tvl_data,
    normalize_price_data,
    map_defillama_to_network,
    UnifiedNetworkData,
)


class TestDefillamaNormalizer:
    
    @pytest.mark.asyncio
    async def test_normalize_tvl_all_eight_networks(self):
        mock_defillama_response = {
            "Ethereum": 100_000_000_000,
            "Solana": 20_000_000_000,
            "Polygon": 5_000_000_000,
            "Arbitrum": 8_000_000_000,
            "Base": 2_000_000_000,
            "Optimism": 3_000_000_000,
            "Avalanche": 1_500_000_000,
            "BNB Chain": 4_000_000_000,
        }
        
        normalized = await normalize_tvl_data(mock_defillama_response)
        
        expected_networks = {"ethereum", "solana", "polygon", "arbitrum", 
                            "base", "optimism", "avalanche", "bsc"}
        
        assert set(normalized.keys()) == expected_networks
        assert normalized["ethereum"] == 100_000_000_000
        assert normalized["solana"] == 20_000_000_000
        assert normalized["polygon"] == 5_000_000_000
    
    @pytest.mark.asyncio
    async def test_normalize_tvl_no_data_loss(self):
        mock_data = {
            "Ethereum": 50_000_000_000,
            "Solana": 10_000_000_000,
        }
        
        normalized = await normalize_tvl_data(mock_data)
        
        assert normalized["ethereum"] == 50_000_000_000
        assert normalized["solana"] == 10_000_000_000
    
    @pytest.mark.asyncio
    async def test_normalize_tvl_unknown_network_ignored(self):
        mock_data = {
            "Ethereum": 100_000_000_000,
            "UnknownChain": 1_000_000_000,
            "Solana": 20_000_000_000,
        }
        
        normalized = await normalize_tvl_data(mock_data)
        
        assert "unknownchain" not in normalized
        assert len(normalized) == 2
    
    def test_map_defillama_to_network_all_ids(self):
        assert map_defillama_to_network("solana") == "solana"
        assert map_defillama_to_network("polygon") == "polygon"
        assert map_defillama_to_network("arbitrum") == "arbitrum"
        assert map_defillama_to_network("base") == "base"
        assert map_defillama_to_network("optimism") == "optimism"
        assert map_defillama_to_network("avalanche") == "avalanche"
        assert map_defillama_to_network("bsc") == "bsc"
        assert map_defillama_to_network("bnb chain") == "bsc"
        assert map_defillama_to_network("ethereum") == "ethereum"
    
    def test_map_defillama_case_insensitive(self):
        assert map_defillama_to_network("ETHEREUM") == "ethereum"
        assert map_defillama_to_network("Solana") == "solana"
        assert map_defillama_to_network("BNB CHAIN") == "bsc"


class TestCoinGeckoNormalizer:
    
    @pytest.mark.asyncio
    async def test_normalize_price_all_eight_networks(self):
        mock_coingecko_response = {
            "ethereum": {"usd": 3000.0, "usd_24h_change": 2.5},
            "solana": {"usd": 100.0, "usd_24h_change": 5.0},
            "matic-network": {"usd": 0.8, "usd_24h_change": -1.2},
            "arbitrum-one": {"usd": 1.5, "usd_24h_change": 3.0},
            "base": {"usd": 2.0, "usd_24h_change": 1.0},
            "optimism": {"usd": 3.0, "usd_24h_change": 0.5},
            "avalanche-2": {"usd": 35.0, "usd_24h_change": -2.0},
            "binancecoin": {"usd": 600.0, "usd_24h_change": 1.5},
        }
        
        normalized = await normalize_price_data(mock_coingecko_response)
        
        expected_networks = {"ethereum", "solana", "polygon", "arbitrum",
                           "base", "optimism", "avalanche", "bsc"}
        
        assert set(normalized.keys()) == expected_networks
    
    @pytest.mark.asyncio
    async def test_normalize_price_critical_fields_not_none(self):
        mock_data = {
            "ethereum": {"usd": 3000.0, "usd_24h_change": 2.5},
            "solana": {"usd": 100.0, "usd_24h_change": 5.0},
        }
        
        normalized = await normalize_price_data(mock_data)
        
        for network in normalized.values():
            assert network["price"] is not None
            assert network["price_change_24h"] is not None
    
    @pytest.mark.asyncio
    async def test_normalize_price_empty_response(self):
        normalized = await normalize_price_data({})
        assert len(normalized) == 0
    
    @pytest.mark.asyncio
    async def test_normalize_price_unknown_coingecko_id_ignored(self):
        mock_data = {
            "ethereum": {"usd": 3000.0},
            "unknown-coin": {"usd": 1.0},
            "solana": {"usd": 100.0},
        }
        
        normalized = await normalize_price_data(mock_data)
        
        assert "unknown-coin" not in normalized
        assert len(normalized) == 2


class TestUnifiedNetworkData:
    
    def test_unified_network_data_creation(self):
        from datetime import datetime
        
        data = UnifiedNetworkData(
            network="ethereum",
            tvl=100_000_000_000.0,
            tvl_change_24h=2.5,
            gas_usd=5.0,
            price=3000.0,
            price_change_24h=2.5,
            market_cap=350_000_000_000.0,
            volume_24h=15_000_000_000.0,
            timestamp=datetime.utcnow(),
        )
        
        assert data.network == "ethereum"
        assert data.tvl == 100_000_000_000.0
        assert data.gas_usd == 5.0
        assert data.price == 3000.0
    
    def test_unified_network_data_fields_not_none(self):
        from datetime import datetime
        
        data = UnifiedNetworkData(
            network="solana",
            tvl=20_000_000_000.0,
            tvl_change_24h=5.0,
            gas_usd=0.001,
            price=100.0,
            price_change_24h=3.0,
            market_cap=40_000_000_000.0,
            volume_24h=2_000_000_000.0,
            timestamp=datetime.utcnow(),
        )
        
        assert data.network is not None
        assert data.tvl is not None
        assert data.tvl_change_24h is not None
        assert data.gas_usd is not None
        assert data.price is not None
        assert data.price_change_24h is not None
        assert data.market_cap is not None
        assert data.volume_24h is not None
