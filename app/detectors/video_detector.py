from __future__ import annotations

import os
import tempfile

import cv2
import numpy as np

from app.detectors.base import DetectorOutput, clamp01
from app.detectors.image_detector import ImageDetector


class VideoDetector:
    def __init__(self) -> None:
        self.image_detector = ImageDetector()

    def analyze(self, video_bytes: bytes) -> DetectorOutput:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name

        try:
            cap = cv2.VideoCapture(tmp_path)
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total <= 0:
                return DetectorOutput(
                    modality="video",
                    deepfake_score=0.5,
                    confidence=0.4,
                    indicators=["Could not decode video frames"],
                )

            sample_count = min(16, max(6, total // 12))
            frame_idxs = np.linspace(0, total - 1, sample_count, dtype=int)

            frame_scores: list[float] = []
            frame_diffs: list[float] = []
            prev_gray = None

            for idx in frame_idxs:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
                ok, frame = cap.read()
                if not ok:
                    continue

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_bytes = cv2.imencode(".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))[1].tobytes()
                out = self.image_detector.analyze(frame_bytes)
                frame_scores.append(out.deepfake_score)

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if prev_gray is not None:
                    diff = float(np.mean(np.abs(gray.astype(np.float32) - prev_gray.astype(np.float32))))
                    frame_diffs.append(diff)
                prev_gray = gray

            cap.release()

            if not frame_scores:
                return DetectorOutput(
                    modality="video",
                    deepfake_score=0.5,
                    confidence=0.4,
                    indicators=["No valid frames sampled"],
                )

            frame_mean = float(np.mean(frame_scores))
            frame_var = float(np.std(frame_scores))
            temporal_motion = float(np.mean(frame_diffs)) if frame_diffs else 0.0

            # Higher frame variance can indicate inconsistent generation quality.
            temporal_score = sigmoid((frame_var - 0.09) / 0.03)
            motion_score = sigmoid((6.0 - temporal_motion) / 2.0)

            score = clamp01(0.6 * frame_mean + 0.25 * temporal_score + 0.15 * motion_score)
            confidence = clamp01(0.5 + abs(score - 0.5) * 0.9)

            indicators: list[str] = []
            if frame_mean > 0.6:
                indicators.append("Multiple frames show image-level deepfake artifacts")
            if temporal_score > 0.6:
                indicators.append("Frame-to-frame inconsistency detected")
            if motion_score > 0.6:
                indicators.append("Unnatural temporal motion smoothness")
            if not indicators:
                indicators.append("No strong temporal/video deepfake patterns detected")

            return DetectorOutput(
                modality="video",
                deepfake_score=score,
                confidence=confidence,
                indicators=indicators,
            )
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + np.exp(-x))
