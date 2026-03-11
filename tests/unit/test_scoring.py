import pytest
from unittest.mock import AsyncMock, patch

from src.scoring.engine import calculate_final_score, calculate_network_score, ALLOWED_NETWORKS
from src.scoring.weights import DEFAULT_WEIGHTS, ScoreWeights


class TestScoringFormula:
    
    def test_weights_sum_to_one(self):
        assert DEFAULT_WEIGHTS.validate() is True
    
    def test_weights_individual_sum(self):
        total = (
            DEFAULT_WEIGHTS.safety
            + DEFAULT_WEIGHTS.reliability
            + DEFAULT_WEIGHTS.cost
            + DEFAULT_WEIGHTS.speed
        )
        assert abs(total - 1.0) < 0.001
    
    def test_custom_weights_validate(self):
        weights = ScoreWeights(safety=0.4, reliability=0.3, cost=0.2, speed=0.1)
        assert weights.validate() is True
    
    def test_invalid_weights_fail_validation(self):
        weights = ScoreWeights(safety=0.5, reliability=0.5, cost=0.5, speed=0.5)
        assert weights.validate() is False
    
    @pytest.mark.asyncio
    async def test_score_between_zero_and_hundred(self):
        for network in ALLOWED_NETWORKS:
            score = await calculate_network_score(network)
            assert 0 <= score.score <= 100
    
    @pytest.mark.asyncio
    async def test_high_tvl_low_gas_better_than_low_tvl_high_gas(self):
        with patch('src.scoring.dimensions.safety.get_safety_metrics') as mock_safety, \
             patch('src.scoring.dimensions.cost.get_cost_metrics') as mock_cost, \
             patch('src.scoring.dimensions.reliability.get_reliability_metrics') as mock_reliability, \
             patch('src.scoring.dimensions.speed.get_speed_metrics') as mock_speed:
            
            mock_safety.return_value = {"score": 90.0, "tvl": 10_000_000_000}
            mock_cost.return_value = {"score": 90.0, "gas_usd": 0.01}
            mock_reliability.return_value = {"score": 80.0, "finality_seconds": 15.0}
            mock_speed.return_value = {"score": 70.0, "tps": 3000}
            
            good_network_score = await calculate_network_score("ethereum")
            
            mock_safety.return_value = {"score": 30.0, "tvl": 100_000_000}
            mock_cost.return_value = {"score": 20.0, "gas_usd": 10.0}
            mock_reliability.return_value = {"score": 50.0, "finality_seconds": 60.0}
            mock_speed.return_value = {"score": 40.0, "tps": 100}
            
            bad_network_score = await calculate_network_score("ethereum")
            
            assert good_network_score.score > bad_network_score.score
    
    @pytest.mark.asyncio
    async def test_all_eight_networks_have_scores(self):
        scores = []
        for network in ALLOWED_NETWORKS:
            score = await calculate_network_score(network)
            scores.append(score)
        
        assert len(scores) == 8
        for score in scores:
            assert score.network in ALLOWED_NETWORKS
            assert score.score is not None
    
    def test_final_score_calculation_with_known_weights(self):
        result = calculate_final_score(
            safety_score=100.0,
            reliability_score=100.0,
            cost_score=100.0,
            speed_score=100.0,
            weights=DEFAULT_WEIGHTS,
        )
        assert result == 100.0
    
    def test_final_score_calculation_mixed_scores(self):
        result = calculate_final_score(
            safety_score=80.0,
            reliability_score=60.0,
            cost_score=40.0,
            speed_score=20.0,
            weights=DEFAULT_WEIGHTS,
        )
        expected = 80 * 0.35 + 60 * 0.30 + 40 * 0.25 + 20 * 0.10
        assert abs(result - expected) < 0.01
        assert 0 <= result <= 100
    
    def test_final_score_zero_scores(self):
        result = calculate_final_score(
            safety_score=0.0,
            reliability_score=0.0,
            cost_score=0.0,
            speed_score=0.0,
        )
        assert result == 0.0
    
    def test_final_score_full_scores(self):
        result = calculate_final_score(
            safety_score=100.0,
            reliability_score=100.0,
            cost_score=100.0,
            speed_score=100.0,
        )
        assert result == 100.0
    
    @pytest.mark.asyncio
    async def test_invalid_network_raises_error(self):
        with pytest.raises(ValueError):
            await calculate_network_score("invalid_network")
    
    def test_allowed_networks_count(self):
        assert len(ALLOWED_NETWORKS) == 8
        expected_networks = {
            "solana", "polygon", "arbitrum", "base",
            "optimism", "avalanche", "bsc", "ethereum",
        }
        assert ALLOWED_NETWORKS == expected_networks
