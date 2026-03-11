from pydantic import BaseModel, Field


class NetworkScore(BaseModel):
    network: str
    score: float = Field(ge=0.0, le=100.0)
    safety_score: float = Field(ge=0.0, le=100.0)
    reliability_score: float = Field(ge=0.0, le=100.0)
    cost_score: float = Field(ge=0.0, le=100.0)
    speed_score: float = Field(ge=0.0, le=100.0)
    tvl: float = 0.0
    gas_usd: float = 0.0
    tps: float = 0.0
    finality_seconds: float = 0.0
    timestamp: str


class ScoreInput(BaseModel):
    amount_usd: float = Field(gt=0)
    asset: str = Field(min_length=1, max_length=20)
    priority: str = Field(pattern="^(cost|speed|safety|balanced)$")


class NetworkScoresResponse(BaseModel):
    scores: list[NetworkScore]
    timestamp: str
