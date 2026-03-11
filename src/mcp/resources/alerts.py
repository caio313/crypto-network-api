from datetime import datetime, timezone
from typing import Any

from src.scoring.engine import ALLOWED_NETWORKS


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


async def get_alerts_active_resource(networks: str | None = None) -> str:
    lines = ["# Active Alerts\n"]
    lines.append(f"Last Updated: {datetime.now(timezone.utc).isoformat()}\n\n")
    
    if networks:
        network_list = [n.strip() for n in networks.split(",")]
        invalid = [n for n in network_list if n not in ALLOWED_NETWORKS]
        if invalid:
            return f"Error: Invalid networks: {invalid}"
        filtered = [a for a in MOCK_ALERTS if a["network"] in network_list]
    else:
        filtered = MOCK_ALERTS
    
    if not filtered:
        lines.append("No active alerts.\n")
    else:
        for alert in filtered:
            severity_icon = "🔴" if alert["severity"] == "critical" else "🟡" if alert["severity"] == "warning" else "ℹ️"
            lines.append(f"{severity_icon} **{alert['network'].upper()}** - {alert['alert_type']}\n")
            lines.append(f"  {alert['message']}\n")
            lines.append(f"  Started: {alert['started_at']}\n\n")
    
    return "".join(lines)
