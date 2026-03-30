from dataclasses import dataclass
from dataclasses import field


@dataclass
class DetectorOutput:
    modality: str
    deepfake_score: float
    confidence: float
    indicators: list[str]
    details: dict[str, float] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return "Suspected Deepfake" if self.deepfake_score >= 0.5 else "Real"


def clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value
