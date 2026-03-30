from __future__ import annotations

import numpy as np
import librosa

from app.detectors.base import DetectorOutput, clamp01


class AudioDetector:
    def analyze(self, audio_bytes: bytes) -> DetectorOutput:
        y, sr = load_audio_from_bytes(audio_bytes)
        if len(y) < sr // 2:
            return DetectorOutput(
                modality="audio",
                deepfake_score=0.5,
                confidence=0.5,
                indicators=["Audio is too short for robust analysis"],
                details={
                    "duration_seconds": round(len(y) / float(sr), 3),
                },
            )

        indicators: list[str] = []

        flatness = float(np.mean(librosa.feature.spectral_flatness(y=y)))
        flatness_score = sigmoid((flatness - 0.18) / 0.05)
        if flatness_score > 0.6:
            indicators.append("High spectral flatness (noise-like synthesis pattern)")

        zcr = librosa.feature.zero_crossing_rate(y=y)[0]
        zcr_var = float(np.std(zcr))
        zcr_score = sigmoid((0.05 - zcr_var) / 0.02)
        if zcr_score > 0.6:
            indicators.append("Over-regular zero-crossing dynamics")

        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        centroid_var = float(np.std(centroid))
        centroid_score = sigmoid((250.0 - centroid_var) / 120.0)
        if centroid_score > 0.6:
            indicators.append("Low spectral variability across frames")

        score = clamp01(0.4 * flatness_score + 0.3 * zcr_score + 0.3 * centroid_score)
        confidence = clamp01(0.5 + abs(score - 0.5) * 0.9)

        if not indicators:
            indicators.append("No strong synthetic-audio artifacts detected")

        return DetectorOutput(
            modality="audio",
            deepfake_score=score,
            confidence=confidence,
            indicators=indicators,
            details={
                "duration_seconds": round(len(y) / float(sr), 3),
                "spectral_flatness_mean": round(flatness, 6),
                "zcr_variance": round(zcr_var, 6),
                "spectral_centroid_variance": round(centroid_var, 3),
                "flatness_signal": round(float(flatness_score), 6),
                "zcr_signal": round(float(zcr_score), 6),
                "centroid_signal": round(float(centroid_score), 6),
            },
        )


def load_audio_from_bytes(audio_bytes: bytes) -> tuple[np.ndarray, int]:
    import io
    import soundfile as sf

    with io.BytesIO(audio_bytes) as f:
        y, sr = sf.read(f, dtype="float32", always_2d=False)

    if y.ndim > 1:
        y = np.mean(y, axis=1)

    if sr != 16000:
        y = librosa.resample(y, orig_sr=sr, target_sr=16000)
        sr = 16000

    y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
    return y, sr


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + np.exp(-x))
