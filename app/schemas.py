from typing import Literal

from pydantic import BaseModel, Field


class DetectionResult(BaseModel):
    modality: Literal["image", "audio", "video"]
    label: Literal["Real", "Suspected Deepfake"]
    risk_level: Literal["Low", "Medium", "High", "Critical"]
    deepfake_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    indicators: list[str] = Field(default_factory=list)
    forensic_details: dict[str, float] = Field(default_factory=dict)
    analysis_summary: str = ""
    analysis_source: Literal["google", "local"] = "local"


class HealthResponse(BaseModel):
    status: str
