import pytest
from unittest.mock import AsyncMock, patch

from src.mcp.tools.get_best_network import (
    get_best_network,
    GetBestNetworkInput,
)
from src.mcp.tools.compare_networks import (
    compare_networks,
    CompareNetworksInput,
)
from src.mcp.tools.estimate_cost import (
    estimate_cost,
    EstimateCostInput,
)
from src.mcp.tools.simulate_transaction import (
    simulate_transaction,
    SimulateTransactionInput,
)
from src.mcp.tools.get_alerts import (
    get_alerts,
    GetAlertsInput,
)
from pydantic import ValidationError


class TestGetBestNetwork:
    @pytest.mark.asyncio
    async def test_get_best_network_valid_input(self):
        input_data = GetBestNetworkInput(
            amount_usd=500.0, asset="USDC", priority="balanced", tier="pro"
        )

        with (
            patch("src.mcp.tools.get_best_network.calculate_all_scores") as mock_scores,
            patch("src.mcp.tools.get_best_network.prioritize_by") as mock_prioritize,
        ):
            from src.models.score import NetworkScore

            mock_scores.return_value = [
                NetworkScore(
                    network="ethereum",
                    score=85.0,
                    safety_score=90.0,
                    reliability_score=85.0,
                    cost_score=80.0,
                    speed_score=70.0,
                    tvl=100_000_000_000,
                    gas_usd=5.0,
                    tps=15,
                    finality_seconds=900,
                    timestamp="2024-01-01T00:00:00Z",
                ),
                NetworkScore(
                    network="polygon",
                    score=75.0,
                    safety_score=70.0,
                    reliability_score=75.0,
                    cost_score=85.0,
                    speed_score=80.0,
                    tvl=5_000_000_000,
                    gas_usd=0.01,
                    tps=7000,
                    finality_seconds=30,
                    timestamp="2024-01-01T00:00:00Z",
                ),
            ]
            mock_prioritize.return_value = mock_scores.return_value

            result = await get_best_network(input_data)

            assert result.success == True
            assert result.reasoning != ""
            assert 0.0 <= result.confidence <= 1.0
            assert result.action != ""
            assert isinstance(result.warnings, list)
            assert isinstance(result.alternatives, list)
            assert isinstance(result.data, dict)
            assert result.data.get("network") == "ethereum"
            assert result.data.get("score") == 85.0

    @pytest.mark.asyncio
    async def test_get_best_network_invalid_priority(self):
        with pytest.raises(ValidationError):
            GetBestNetworkInput(amount_usd=500.0, asset="USDC", priority="invalid_priority")

    @pytest.mark.asyncio
    async def test_get_best_network_negative_amount(self):
        with pytest.raises(ValidationError):
            GetBestNetworkInput(amount_usd=-100.0, asset="USDC", priority="cost")

    @pytest.mark.asyncio
    async def test_get_best_network_empty_asset(self):
        with pytest.raises(ValidationError):
            GetBestNetworkInput(amount_usd=500.0, asset="", priority="safety")

    @pytest.mark.asyncio
    async def test_get_best_network_zero_amount(self):
        with pytest.raises(ValidationError):
            GetBestNetworkInput(amount_usd=0.0, asset="ETH", priority="balanced")


class TestCompareNetworks:
    @pytest.mark.asyncio
    async def test_compare_networks_valid_input(self):
        input_data = CompareNetworksInput(
            networks=["ethereum", "polygon", "arbitrum"],
            amount_usd=1000.0,
            asset="USDC",
            tier="pro",
        )

        with patch("src.mcp.tools.compare_networks.calculate_network_score") as mock_score:
            from src.models.score import NetworkScore

            mock_score.return_value = NetworkScore(
                network="ethereum",
                score=85.0,
                safety_score=90.0,
                reliability_score=85.0,
                cost_score=80.0,
                speed_score=70.0,
                tvl=100_000_000_000,
                gas_usd=5.0,
                tps=15,
                finality_seconds=900,
                timestamp="2024-01-01T00:00:00Z",
            )

            result = await compare_networks(input_data)

            assert result.success == True
            assert result.reasoning != ""
            assert 0.0 <= result.confidence <= 1.0
            assert result.action != ""
            assert isinstance(result.warnings, list)
            assert isinstance(result.alternatives, list)
            assert isinstance(result.data, dict)
            assert len(result.data.get("comparison", [])) > 0

    @pytest.mark.asyncio
    async def test_compare_networks_invalid_network(self):
        with pytest.raises(ValidationError):
            CompareNetworksInput(
                networks=["ethereum", "invalid_network"], amount_usd=1000.0, asset="USDC"
            )

    @pytest.mark.asyncio
    async def test_compare_networks_single_network(self):
        with pytest.raises(ValidationError):
            CompareNetworksInput(networks=["ethereum"], amount_usd=1000.0, asset="USDC")

    @pytest.mark.asyncio
    async def test_compare_networks_too_many_networks(self):
        with pytest.raises(ValidationError):
            CompareNetworksInput(
                networks=[
                    "ethereum",
                    "polygon",
                    "arbitrum",
                    "base",
                    "optimism",
                    "avalanche",
                    "bsc",
                    "solana",
                    "extra",
                ],
                amount_usd=1000.0,
                asset="USDC",
            )

    @pytest.mark.asyncio
    async def test_compare_networks_negative_amount(self):
        with pytest.raises(ValidationError):
            CompareNetworksInput(networks=["ethereum", "polygon"], amount_usd=-100.0, asset="USDC")


class TestEstimateCost:
    @pytest.mark.asyncio
    async def test_estimate_cost_valid_input(self):
        input_data = EstimateCostInput(network="ethereum", amount_usd=500.0, token="USDC")

        result = await estimate_cost(input_data)

        assert result.success == True
        assert result.reasoning != ""
        assert 0.0 <= result.confidence <= 1.0
        assert result.action != ""
        assert isinstance(result.warnings, list)
        assert isinstance(result.alternatives, list)
        assert isinstance(result.data, dict)
        assert result.data.get("fee_usd") > 0
        assert result.data.get("fee_native") > 0
        assert result.data.get("confirmation_seconds") > 0

    @pytest.mark.asyncio
    async def test_estimate_cost_invalid_network(self):
        input_data = EstimateCostInput(network="invalid_network", amount_usd=500.0, token="USDC")

        with pytest.raises(ValueError, match="Invalid network"):
            await estimate_cost(input_data)

    @pytest.mark.asyncio
    async def test_estimate_cost_all_valid_networks(self):
        valid_networks = [
            "ethereum",
            "solana",
            "polygon",
            "arbitrum",
            "base",
            "optimism",
            "avalanche",
            "bsc",
        ]

        for network in valid_networks:
            input_data = EstimateCostInput(network=network, amount_usd=100.0, token="ETH")
            result = await estimate_cost(input_data)
            assert result.success == True
            assert result.data.get("fee_usd") > 0

    @pytest.mark.asyncio
    async def test_estimate_cost_negative_amount(self):
        with pytest.raises(ValidationError):
            EstimateCostInput(network="ethereum", amount_usd=-100.0, token="USDC")

    @pytest.mark.asyncio
    async def test_estimate_cost_empty_token(self):
        with pytest.raises(ValidationError):
            EstimateCostInput(network="ethereum", amount_usd=500.0, token="")


class TestSimulateTransaction:
    @pytest.mark.asyncio
    async def test_simulate_transaction_free_tier_raises_403(self):
        input_data = SimulateTransactionInput(
            from_network="ethereum",
            to_network="polygon",
            amount_usd=500.0,
            asset="USDC",
            tier="FREE",
        )

        with pytest.raises(PermissionError) as exc_info:
            await simulate_transaction(input_data)

        assert "plan_required" in str(exc_info.value)
        assert "PRO" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_simulate_transaction_pro_tier_allowed(self):
        input_data = SimulateTransactionInput(
            from_network="ethereum",
            to_network="polygon",
            amount_usd=500.0,
            asset="USDC",
            tier="PRO",
        )

        result = await simulate_transaction(input_data)

        assert len(result.steps) > 0
        assert result.total_fee_usd > 0
        assert result.total_time_seconds > 0
        assert result.bridge_used is not None
        assert len(result.risks) > 0

    @pytest.mark.asyncio
    async def test_simulate_transaction_enterprise_tier_allowed(self):
        input_data = SimulateTransactionInput(
            from_network="base",
            to_network="avalanche",
            amount_usd=1000.0,
            asset="ETH",
            tier="ENTERPRISE",
        )

        result = await simulate_transaction(input_data)

        assert result.total_fee_usd > 0

    @pytest.mark.asyncio
    async def test_simulate_transaction_free_tier_network_not_allowed(self):
        input_data = SimulateTransactionInput(
            from_network="base", to_network="polygon", amount_usd=500.0, asset="USDC", tier="FREE"
        )

        with pytest.raises(ValueError, match="not available in FREE plan"):
            await simulate_transaction(input_data)

    @pytest.mark.asyncio
    async def test_simulate_transaction_invalid_from_network(self):
        with pytest.raises(ValidationError):
            SimulateTransactionInput(
                from_network="", to_network="polygon", amount_usd=500.0, asset="USDC"
            )

    @pytest.mark.asyncio
    async def test_simulate_transaction_negative_amount(self):
        with pytest.raises(ValidationError):
            SimulateTransactionInput(
                from_network="ethereum", to_network="polygon", amount_usd=-100.0, asset="USDC"
            )


class TestGetAlerts:
    @pytest.mark.asyncio
    async def test_get_alerts_valid_input(self):
        input_data = GetAlertsInput()

        result = await get_alerts(input_data)

        assert result.success == True
        assert result.reasoning != ""
        assert 0.0 <= result.confidence <= 1.0
        assert result.action != ""
        assert isinstance(result.warnings, list)
        assert isinstance(result.alternatives, list)
        assert isinstance(result.data, dict)
        alerts = result.data.get("alerts", [])
        assert len(alerts) > 0
        for alert in alerts:
            assert alert.get("network") is not None
            assert alert.get("severity") is not None
            assert alert.get("alert_type") is not None
            assert alert.get("message") is not None

    @pytest.mark.asyncio
    async def test_get_alerts_filtered_by_networks(self):
        input_data = GetAlertsInput(networks=["ethereum", "polygon"])

        result = await get_alerts(input_data)

        alerts = result.data.get("alerts", [])
        for alert in alerts:
            assert alert.get("network") in ["ethereum", "polygon"]

    @pytest.mark.asyncio
    async def test_get_alerts_invalid_network(self):
        input_data = GetAlertsInput(networks=["ethereum", "invalid_network"])

        with pytest.raises(ValueError, match="Invalid networks"):
            await get_alerts(input_data)

    @pytest.mark.asyncio
    async def test_get_alerts_all_valid_networks(self):
        valid_networks = [
            "ethereum",
            "solana",
            "polygon",
            "arbitrum",
            "base",
            "optimism",
            "avalanche",
            "bsc",
        ]

        input_data = GetAlertsInput(networks=valid_networks)

        result = await get_alerts(input_data)

        alerts = result.data.get("alerts", [])
        assert len(alerts) > 0

    @pytest.mark.asyncio
    async def test_get_alerts_empty_networks_filter(self):
        input_data = GetAlertsInput(networks=[])

        result = await get_alerts(input_data)

        alerts = result.data.get("alerts", [])
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_get_alerts_response_structure(self):
        input_data = GetAlertsInput()

        result = await get_alerts(input_data)

        alerts = result.data.get("alerts", [])
        for alert in alerts:
            assert "network" in alert
            assert "severity" in alert
            assert "alert_type" in alert
            assert "message" in alert
            assert "started_at" in alert


class TestMCPToolsIntegration:
    @pytest.mark.asyncio
    async def test_all_tools_importable(self):
        from src.mcp.tools import (
            get_best_network as gbn,
            compare_networks as cn,
            estimate_cost as ec,
            simulate_transaction as st,
            get_alerts as ga,
        )

        assert gbn is not None
        assert cn is not None
        assert ec is not None
        assert st is not None
        assert ga is not None

    @pytest.mark.asyncio
    async def test_tools_have_pydantic_models(self):
        from src.mcp.tools.get_best_network import GetBestNetworkInput
        from src.mcp.tools.compare_networks import CompareNetworksInput
        from src.mcp.tools.estimate_cost import EstimateCostInput
        from src.mcp.tools.simulate_transaction import SimulateTransactionInput
        from src.mcp.tools.get_alerts import GetAlertsInput

        assert GetBestNetworkInput is not None
        assert CompareNetworksInput is not None
        assert EstimateCostInput is not None
        assert SimulateTransactionInput is not None
        assert GetAlertsInput is not None
