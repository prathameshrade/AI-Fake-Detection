from typing import Literal

from pydantic import BaseModel, Field


class DetectionResult(BaseModel):
    modality: Literal["image", "audio", "video"]
    label: Literal["Real", "Suspected Deepfake"]
    deepfake_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    indicators: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
