from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from src.models.response import AIFirstResponse
from src.scoring.engine import ALLOWED_NETWORKS, validate_network


class AlertItem(BaseModel):
    network: str
    severity: str
    alert_type: str
    message: str
    started_at: str


class GetAlertsInput(BaseModel):
    networks: list[str] | None = Field(None, description="Filter by network IDs")


class GetAlertsOutput(BaseModel):
    alerts: list[AlertItem]


MOCK_ALERTS: list[dict[str, Any]] = [
    {
        "network": "ethereum",
        "severity": "info",
        "alert_type": "high_gas",
        "message": "Gas prices are currently elevated. Consider using during off-peak hours.",
        "started_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "network": "polygon",
        "severity": "warning",
        "alert_type": "low_tvl",
        "message": "TVL has decreased by 15% over the past week.",
        "started_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "network": "arbitrum",
        "severity": "info",
        "alert_type": "network_upgrade",
        "message": "Scheduled network upgrade in 48 hours.",
        "started_at": datetime.now(timezone.utc).isoformat(),
    },
]


async def get_alerts(input_data: GetAlertsInput) -> AIFirstResponse:
    if input_data.networks is not None and len(input_data.networks) == 0:
        return AIFirstResponse.create(
            success=True,
            data={"alerts": [], "networks_clear": list(ALLOWED_NETWORKS)},
            reasoning="All networks are clear. No active alerts.",
            confidence=0.98,
            action="All networks clear. Proceed normally.",
            warnings=[],
            alternatives=[],
            data_freshness_seconds=0,
        )

    if input_data.networks is not None and len(input_data.networks) > 0:
        invalid = [n for n in input_data.networks if n not in ALLOWED_NETWORKS]
        if invalid:
            raise ValueError(f"Invalid networks: {invalid}. Allowed: {ALLOWED_NETWORKS}")

        filtered = [a for a in MOCK_ALERTS if a["network"] in input_data.networks]
    else:
        filtered = MOCK_ALERTS

    alerts = [AlertItem(**a) for a in filtered]

    networks_with_alerts = list(set(a["network"] for a in filtered))
    networks_clear = [n for n in ALLOWED_NETWORKS if n not in networks_with_alerts]

    if len(networks_with_alerts) == 0:
        reasoning = "All networks are clear. No active alerts at this time."
        action = "All networks clear. Proceed normally."
    elif len(networks_with_alerts) == 1:
        reasoning = f"1 network has active alerts: {networks_with_alerts[0]}. {len(networks_clear)} other networks are clear."
        action = f"Avoid {networks_with_alerts[0]}. Use {networks_clear[0] if networks_clear else 'another network'} instead."
    else:
        reasoning = f"{len(networks_with_alerts)} networks have active alerts: {', '.join(networks_with_alerts)}. {len(networks_clear)} networks are clear."
        action = f"Avoid {', '.join(networks_with_alerts)}. Use {networks_clear[0] if networks_clear else 'another network'} instead."

    return AIFirstResponse.create(
        success=True,
        data={
            "alerts": [a.model_dump() for a in alerts],
            "networks_clear": networks_clear,
        },
        reasoning=reasoning,
        confidence=0.98,
        action=action,
        warnings=networks_with_alerts,
        alternatives=[],
        data_freshness_seconds=0,
    )
