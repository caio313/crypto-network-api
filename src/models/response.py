from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class AIFirstResponse(BaseModel):
    success: bool = True
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_freshness_seconds: int = 0
    data: dict[str, Any] = {}
    reasoning: str = ""
    confidence: float = 0.0
    action: str = ""
    warnings: list[str] = []
    alternatives: list[dict[str, Any]] = []

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if v < 0.0:
            return 0.0
        if v > 1.0:
            return 1.0
        return v

    @model_validator(mode="before")
    @classmethod
    def ensure_no_nulls(cls, values: dict[str, Any]) -> dict[str, Any]:
        if values.get("confidence", 0) < 0:
            values["confidence"] = 0.0
        elif values.get("confidence", 0) > 1:
            values["confidence"] = 1.0

        if values.get("data") is None:
            values["data"] = {}
        if values.get("reasoning") is None:
            values["reasoning"] = ""
        if values.get("action") is None:
            values["action"] = ""
        if values.get("warnings") is None:
            values["warnings"] = []
        if values.get("alternatives") is None:
            values["alternatives"] = []

        return values

    @classmethod
    def create(
        cls,
        success: bool = True,
        data: dict[str, Any] | None = None,
        reasoning: str = "",
        confidence: float = 0.0,
        action: str = "",
        warnings: list[str] | None = None,
        alternatives: list[dict[str, Any]] | None = None,
        data_freshness_seconds: int = 0,
    ) -> "AIFirstResponse":
        return cls(
            success=success,
            timestamp=datetime.now(timezone.utc),
            data_freshness_seconds=data_freshness_seconds,
            data=data or {},
            reasoning=reasoning,
            confidence=confidence,
            action=action,
            warnings=warnings or [],
            alternatives=alternatives or [],
        )
