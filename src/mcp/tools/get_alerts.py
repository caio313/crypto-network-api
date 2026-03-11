from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

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


async def get_alerts(input_data: GetAlertsInput) -> GetAlertsOutput:
    if input_data.networks is not None and len(input_data.networks) == 0:
        return GetAlertsOutput(alerts=[])
    
    if input_data.networks is not None and len(input_data.networks) > 0:
        invalid = [n for n in input_data.networks if n not in ALLOWED_NETWORKS]
        if invalid:
            raise ValueError(f"Invalid networks: {invalid}. Allowed: {ALLOWED_NETWORKS}")
        
        filtered = [a for a in MOCK_ALERTS if a["network"] in input_data.networks]
    else:
        filtered = MOCK_ALERTS
    
    alerts = [AlertItem(**a) for a in filtered]
    
    return GetAlertsOutput(alerts=alerts)
