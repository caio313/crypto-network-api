from datetime import datetime, timezone

from src.scoring.dimensions.cost import NETWORK_GAS


async def get_gas_current_resource() -> str:
    lines = ["# Current Gas Prices\n"]
    lines.append(f"Last Updated: {datetime.now(timezone.utc).isoformat()}\n\n")
    
    for network, data in sorted(NETWORK_GAS.items(), key=lambda x: x[1].get("gas_usd", 0)):
        lines.append(f"## {network.upper()}\n")
        lines.append(f"- Current Gas: ${data.get('gas_usd', 0):.4f}\n")
        lines.append(f"- 7-Day Average: ${data.get('avg_7d_usd', 0):.4f}\n")
        lines.append(f"- 90th Percentile: ${data.get('p90_usd', 0):.4f}\n")
        lines.append("\n")
    
    return "".join(lines)
