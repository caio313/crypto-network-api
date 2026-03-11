from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.api.deps import CacheDep
from src.core.logging import structlog
from src.scoring.engine import ALLOWED_NETWORKS, validate_network
from src.scoring.dimensions.cost import NETWORK_GAS

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/alerts", tags=["alerts"])


class AlertResponse(BaseModel):
    network: str
    severity: str
    alert_type: str
    message: str
    started_at: str
    resolved_at: str | None = None


class AlertsResponse(BaseModel):
    alerts: list[AlertResponse]
    count: int
    timestamp: str


ALERT_SEVERITY_LEVELS = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


async def check_gas_congestion_alerts(cache: CacheDep) -> list[dict[str, Any]]:
    alerts = []
    gas_data = await cache.get_gas_prices()
    
    if not gas_data:
        return alerts
    
    for network in ALLOWED_NETWORKS:
        current_gas = gas_data.get(network, {}).get("gas_usd", 0)
        if current_gas == 0:
            current_gas = NETWORK_GAS.get(network, {}).get("gas_usd", 0)
        
        p90_gas = NETWORK_GAS.get(network, {}).get("p90_usd", 0)
        
        if p90_gas > 0 and current_gas > p90_gas:
            severity = "medium"
            if current_gas > p90_gas * 1.5:
                severity = "high"
            if current_gas > p90_gas * 2:
                severity = "critical"
            
            alerts.append({
                "network": network,
                "severity": severity,
                "alert_type": "gas_congestion",
                "message": f"Network {network} is experiencing congestion. Current gas fee (${current_gas:.4f}) exceeds 90th percentile (${p90_gas:.4f}). Transaction costs are significantly higher than usual.",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "resolved_at": None,
            })
    
    return alerts


async def check_tvl_drop_alerts(cache: CacheDep) -> list[dict[str, Any]]:
    alerts = []
    current_tvl = await cache.get_tvl_data()
    
    if not current_tvl:
        return alerts
    
    for network in ALLOWED_NETWORKS:
        current_value = current_tvl.get(network, 0)
        
        tvl_history = await cache.get_tvl_history(network)
        if not tvl_history:
            historical = tvl_history.get("history", []) if isinstance(tvl_history, dict) else []
        else:
            historical = tvl_history.get("history", []) if isinstance(tvl_history, dict) else []
        
        if len(historical) >= 2:
            previous_value = historical[0].get("tvl", current_value) if isinstance(historical[0], dict) else current_value
            
            if previous_value > 0:
                drop_percent = ((previous_value - current_value) / previous_value) * 100
                
                if drop_percent > 20:
                    severity = "high"
                    if drop_percent > 40:
                        severity = "critical"
                    
                    alerts.append({
                        "network": network,
                        "severity": severity,
                        "alert_type": "tvl_drop",
                        "message": f"Network {network} has experienced a TVL drop of {drop_percent:.1f}% in the last hour. Current TVL: ${current_value:,.0f}, Previous TVL: ${previous_value:,.0f}. This may indicate a security incident or loss of user confidence.",
                        "started_at": datetime.now(timezone.utc).isoformat(),
                        "resolved_at": None,
                    })
    
    return alerts


async def check_uptime_alerts(cache: CacheDep) -> list[dict[str, Any]]:
    alerts = []
    network_status = await cache.get_network_status()
    
    if not network_status:
        return alerts
    
    status_data = network_status.get("status", {})
    
    for network in ALLOWED_NETWORKS:
        network_data = status_data.get(network, {})
        is_online = network_data.get("online", True)
        last_check = network_data.get("last_check")
        
        if not is_online:
            severity = "high"
            if last_check:
                try:
                    last_check_time = datetime.fromisoformat(last_check.replace("Z", "+00:00"))
                    time_diff = datetime.now(timezone.utc) - last_check_time
                    if time_diff > timedelta(hours=1):
                        severity = "critical"
                except Exception:
                    pass
            
            alerts.append({
                "network": network,
                "severity": severity,
                "alert_type": "uptime_incident",
                "message": f"Network {network} is not responding to RPC requests. The network may be experiencing an outage or connectivity issues. Last successful check: {last_check or 'unknown'}.",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "resolved_at": None,
            })
    
    return alerts


async def generate_alerts(cache: CacheDep) -> list[dict[str, Any]]:
    all_alerts = []
    
    gas_alerts = await check_gas_congestion_alerts(cache)
    all_alerts.extend(gas_alerts)
    
    tvl_alerts = await check_tvl_drop_alerts(cache)
    all_alerts.extend(tvl_alerts)
    
    uptime_alerts = await check_uptime_alerts(cache)
    all_alerts.extend(uptime_alerts)
    
    all_alerts.sort(
        key=lambda x: ALERT_SEVERITY_LEVELS.get(x.get("severity", "low"), 0),
        reverse=True,
    )
    
    return all_alerts


@router.get("/", response_model=AlertsResponse)
async def list_alerts(
    cache: CacheDep,
    network: str | None = Query(None),
    severity: str | None = Query(None, pattern="^(low|medium|high|critical|info|warning)$"),
    regenerate: bool = Query(False),
) -> AlertsResponse:
    if network and not validate_network(network):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid network. Must be one of: {ALLOWED_NETWORKS}",
        )
    
    if regenerate:
        all_alerts = await generate_alerts(cache)
        await cache.set_alerts(all_alerts)
    else:
        cached = await cache.get_alerts()
        
        if cached:
            all_alerts = cached.get("alerts", [])
        else:
            all_alerts = await generate_alerts(cache)
            await cache.set_alerts(all_alerts)
    
    if network:
        all_alerts = [a for a in all_alerts if a.get("network") == network]
    
    if severity:
        all_alerts = [a for a in all_alerts if a.get("severity") == severity]
    
    alerts_response = [
        AlertResponse(
            network=a.get("network", ""),
            severity=a.get("severity", "low"),
            alert_type=a.get("alert_type", ""),
            message=a.get("message", ""),
            started_at=a.get("started_at", ""),
            resolved_at=a.get("resolved_at"),
        )
        for a in all_alerts
    ]
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    return AlertsResponse(
        alerts=alerts_response,
        count=len(alerts_response),
        timestamp=timestamp,
    )


@router.get("/{network_id}", response_model=AlertsResponse)
async def get_network_alerts(
    network_id: str,
    cache: CacheDep,
) -> AlertsResponse:
    if not validate_network(network_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid network. Must be one of: {ALLOWED_NETWORKS}",
        )
    
    all_alerts = await generate_alerts(cache)
    network_alerts = [a for a in all_alerts if a.get("network") == network_id]
    
    alerts_response = [
        AlertResponse(
            network=a.get("network", ""),
            severity=a.get("severity", "low"),
            alert_type=a.get("alert_type", ""),
            message=a.get("message", ""),
            started_at=a.get("started_at", ""),
            resolved_at=a.get("resolved_at"),
        )
        for a in network_alerts
    ]
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    return AlertsResponse(
        alerts=alerts_response,
        count=len(alerts_response),
        timestamp=timestamp,
    )
