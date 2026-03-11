from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class TransactionStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class PriorityLevel(str, Enum):
    COST = "cost"
    SPEED = "speed"
    SAFETY = "safety"
    BALANCED = "balanced"


class TransactionRequest(BaseModel):
    from_network: str = Field(..., min_length=1)
    to_network: str = Field(..., min_length=1)
    amount_usd: float = Field(gt=0)
    asset: str = Field(min_length=1, max_length=20)
    priority: PriorityLevel = PriorityLevel.BALANCED


class TransactionEstimate(BaseModel):
    from_network: str
    to_network: str
    amount_usd: float
    asset: str
    fee_usd: float
    fee_native: float
    estimated_seconds: int
    bridge_used: str | None = None
    steps: list[str]
    risks: list[str]


class NetworkGas(BaseModel):
    network: str
    gas_usd: float
    gas_native: float
    gas_gwei: float | None = None
    updated_at: datetime


class GasHistoryPoint(BaseModel):
    timestamp: datetime
    gas_usd: float


class NetworkAlerts(BaseModel):
    network: str
    severity: str
    alert_type: str
    message: str
    started_at: datetime
    resolved_at: datetime | None = None
