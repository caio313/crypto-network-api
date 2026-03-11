from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from src.core.config import settings
from src.core.logging import structlog
from src.mcp.prompts.transaction_advisor import get_transaction_advisor_prompt
from src.mcp.resources import alerts as alerts_resource
from src.mcp.resources import gas as gas_resource
from src.mcp.resources import scores as scores_resource
from src.mcp.tools import (
    compare_networks,
    estimate_cost,
    get_alerts,
    get_best_network,
    simulate_transaction,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/mcp", tags=["mcp"])


async def handle_tool_call(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        match tool_name:
            case "get_best_network":
                from src.mcp.tools.get_best_network import GetBestNetworkInput
                input_data = GetBestNetworkInput(**arguments)
                result = await get_best_network.get_best_network(input_data)
                return result.model_dump()
            
            case "compare_networks":
                from src.mcp.tools.compare_networks import CompareNetworksInput
                input_data = CompareNetworksInput(**arguments)
                result = await compare_networks.compare_networks(input_data)
                return result.model_dump()
            
            case "estimate_transaction_cost":
                from src.mcp.tools.estimate_cost import EstimateCostInput
                input_data = EstimateCostInput(**arguments)
                result = await estimate_cost.estimate_cost(input_data)
                return result.model_dump()
            
            case "simulate_transaction":
                from src.mcp.tools.simulate_transaction import SimulateTransactionInput
                input_data = SimulateTransactionInput(**arguments)
                result = await simulate_transaction.simulate_transaction(input_data)
                return result.model_dump()
            
            case "get_network_alerts":
                from src.mcp.tools.get_alerts import GetAlertsInput
                input_data = GetAlertsInput(**arguments)
                result = await get_alerts.get_alerts(input_data)
                return result.model_dump()
            
            case _:
                raise ValueError(f"Unknown tool: {tool_name}")
    
    except PermissionError as e:
        logger.warning("mcp_tier_restriction", tool=tool_name, error=str(e))
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        logger.error("mcp_validation_error", tool=tool_name, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("mcp_tool_error", tool=tool_name, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


async def handle_resource_read(uri: str) -> str:
    try:
        if uri == "crypto://networks/scores":
            return await scores_resource.get_network_scores_resource()
        
        if uri == "crypto://gas/current":
            return await gas_resource.get_gas_current_resource()
        
        if uri.startswith("crypto://alerts/active"):
            networks = None
            if "?" in uri:
                params = uri.split("?")[1]
                if "networks=" in params:
                    networks = params.split("networks=")[1].split("&")[0]
            return await alerts_resource.get_alerts_active_resource(networks)
        
        raise ValueError(f"Unknown resource: {uri}")
    
    except Exception as e:
        logger.error("mcp_resource_error", uri=uri, error=str(e))
        raise HTTPException(status_code=500, detail="Error reading resource")


@router.get("/tools")
async def list_tools() -> dict[str, Any]:
    return {
        "tools": [
            {
                "name": "get_best_network",
                "description": "Get the best network for a transaction based on amount, asset, and priority",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "amount_usd": {"type": "number", "description": "Amount in USD"},
                        "asset": {"type": "string", "description": "Asset symbol (e.g., USDC)"},
                        "priority": {"type": "string", "enum": ["cost", "speed", "safety", "balanced"]},
                    },
                    "required": ["amount_usd", "asset", "priority"],
                },
            },
            {
                "name": "compare_networks",
                "description": "Compare multiple networks side by side",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "networks": {"type": "array", "items": {"type": "string"}},
                        "amount_usd": {"type": "number"},
                        "asset": {"type": "string"},
                    },
                    "required": ["networks", "amount_usd", "asset"],
                },
            },
            {
                "name": "estimate_transaction_cost",
                "description": "Estimate the exact cost of a transaction on a specific network",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "network": {"type": "string"},
                        "amount_usd": {"type": "number"},
                        "token": {"type": "string"},
                    },
                    "required": ["network", "amount_usd", "token"],
                },
            },
            {
                "name": "simulate_transaction",
                "description": "Simulate a cross-chain transaction with full steps and risks (PRO only)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "from_network": {"type": "string"},
                        "to_network": {"type": "string"},
                        "amount_usd": {"type": "number"},
                        "asset": {"type": "string"},
                        "tier": {"type": "string", "default": "FREE"},
                    },
                    "required": ["from_network", "to_network", "amount_usd", "asset"],
                },
            },
            {
                "name": "get_network_alerts",
                "description": "Get active alerts for specified networks or all networks",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "networks": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
        ],
    }


@router.post("/tools/call")
async def call_tool(request: dict[str, Any]) -> dict[str, Any]:
    tool_name = request.get("name")
    arguments = request.get("arguments", {})
    
    if not tool_name:
        raise HTTPException(status_code=400, detail="Missing tool name")
    
    result = await handle_tool_call(tool_name, arguments)
    return {"content": [{"type": "text", "text": str(result)}]}


@router.get("/resources")
async def list_resources() -> dict[str, Any]:
    return {
        "resources": [
            {
                "uri": "crypto://networks/scores",
                "name": "Network Scores",
                "description": "Current scores for all monitored networks",
                "mimeType": "text/markdown",
            },
            {
                "uri": "crypto://gas/current",
                "name": "Current Gas Prices",
                "description": "Current gas prices for all networks",
                "mimeType": "text/markdown",
            },
            {
                "uri": "crypto://alerts/active",
                "name": "Active Alerts",
                "description": "Currently active alerts for all networks",
                "mimeType": "text/markdown",
            },
        ],
    }


@router.get("/resources/{path:path}")
async def read_resource(path: str) -> JSONResponse:
    uri = f"crypto://{path}"
    content = await handle_resource_read(uri)
    return JSONResponse(content=content, media_type="text/markdown")


@router.get("/prompts")
async def list_prompts() -> dict[str, Any]:
    return {
        "prompts": [
            {
                "name": "transaction_advisor",
                "description": "Get guidance on which network to use for a transaction",
                "arguments": [],
            },
        ],
    }


@router.get("/prompts/{prompt_name}")
async def get_prompt(prompt_name: str) -> dict[str, Any]:
    if prompt_name == "transaction_advisor":
        return {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": get_transaction_advisor_prompt(),
                    },
                },
            ],
        }
    raise HTTPException(status_code=404, detail="Prompt not found")
