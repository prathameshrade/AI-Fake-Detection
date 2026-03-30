from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from app.detectors.base import DetectorOutput, clamp01


class ImageDetector:
    def analyze(self, image_bytes: bytes) -> DetectorOutput:
        pil_img = Image.open(io_bytes(image_bytes)).convert("RGB")
        arr = np.array(pil_img)
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        indicators: list[str] = []

        # Blur and smoothing signal.
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        blur_score = sigmoid((120.0 - lap_var) / 30.0)
        if blur_score > 0.65:
            indicators.append("Unusually smooth/blurred texture")

        # High-frequency inconsistency signal.
        hf_ratio = high_frequency_ratio(gray)
        hf_score = sigmoid((0.22 - hf_ratio) / 0.05)
        if hf_score > 0.6:
            indicators.append("Abnormal high-frequency content")

        # Blockiness / compression artifact signal.
        blockiness = jpeg_blockiness(gray)
        block_score = sigmoid((blockiness - 7.0) / 2.0)
        if block_score > 0.6:
            indicators.append("Compression/block boundary artifacts")

        score = clamp01(0.42 * blur_score + 0.33 * hf_score + 0.25 * block_score)
        confidence = clamp01(0.5 + abs(score - 0.5) * 0.9)

        if not indicators:
            indicators.append("No strong artifact patterns detected")

        return DetectorOutput(
            modality="image",
            deepfake_score=score,
            confidence=confidence,
            indicators=indicators,
            details={
                "laplacian_variance": round(lap_var, 3),
                "high_frequency_ratio": round(hf_ratio, 6),
                "jpeg_blockiness": round(blockiness, 4),
                "blur_signal": round(float(blur_score), 6),
                "frequency_signal": round(float(hf_score), 6),
                "compression_signal": round(float(block_score), 6),
            },
        )


def io_bytes(data: bytes):
    import io

    return io.BytesIO(data)


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + np.exp(-x))


def high_frequency_ratio(gray: np.ndarray) -> float:
    fft = np.fft.fftshift(np.fft.fft2(gray.astype(np.float32)))
    magnitude = np.abs(fft)
    h, w = gray.shape
    cy, cx = h // 2, w // 2
    low_r = min(h, w) // 8

    y, x = np.ogrid[:h, :w]
    dist = np.sqrt((y - cy) ** 2 + (x - cx) ** 2)
    low_mask = dist <= low_r
    high_mask = dist > low_r

    low_energy = float(magnitude[low_mask].sum()) + 1e-6
    high_energy = float(magnitude[high_mask].sum())
    return high_energy / (low_energy + high_energy + 1e-6)


def jpeg_blockiness(gray: np.ndarray) -> float:
    h, w = gray.shape
    if h < 16 or w < 16:
        return 0.0

    v_lines = []
    for x in range(8, w - 1, 8):
        diff = np.abs(gray[:, x].astype(np.float32) - gray[:, x - 1].astype(np.float32))
        v_lines.append(diff.mean())

    h_lines = []
    for y in range(8, h - 1, 8):
        diff = np.abs(gray[y, :].astype(np.float32) - gray[y - 1, :].astype(np.float32))
        h_lines.append(diff.mean())

    if not v_lines and not h_lines:
        return 0.0
    return float(np.mean(v_lines + h_lines))
