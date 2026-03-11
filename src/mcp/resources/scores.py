from datetime import datetime, timezone

from src.scoring.engine import calculate_all_scores


async def get_network_scores_resource() -> str:
    scores = await calculate_all_scores()
    
    lines = ["# Network Scores\n"]
    lines.append(f"Last Updated: {datetime.now(timezone.utc).isoformat()}\n\n")
    
    for score in sorted(scores, key=lambda s: s.score, reverse=True):
        lines.append(f"## {score.network.upper()}\n")
        lines.append(f"- Overall Score: {score.score}/100\n")
        lines.append(f"- Safety: {score.safety_score}/100\n")
        lines.append(f"- Reliability: {score.reliability_score}/100\n")
        lines.append(f"- Cost: {score.cost_score}/100\n")
        lines.append(f"- Speed: {score.speed_score}/100\n")
        lines.append(f"- TVL: ${score.tvl:,.0f}\n")
        lines.append(f"- Gas (USD): ${score.gas_usd:.4f}\n")
        lines.append(f"- TPS: {score.tps:,.0f}\n")
        lines.append(f"- Finality: {score.finality_seconds}s\n")
        lines.append("\n")
    
    return "".join(lines)
