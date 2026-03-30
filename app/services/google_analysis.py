from __future__ import annotations

import json
import os
from urllib import error, request


class GoogleAnalysisClient:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        self.model = model or os.getenv("GOOGLE_MODEL", "gemini-1.5-flash-latest")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def summarize_result(
        self,
        modality: str,
        label: str,
        deepfake_score: float,
        confidence: float,
        indicators: list[str],
        details: dict[str, float],
    ) -> str | None:
        if not self.enabled:
            return None

        prompt = self._build_prompt(modality, label, deepfake_score, confidence, indicators, details)
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt,
                        }
                    ]
                }
            ]
        }

        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )

        req = request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (error.URLError, TimeoutError, ValueError):
            return None

        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError):
            return None

        if not isinstance(text, str) or not text.strip():
            return None

        return text.strip()

    def _build_prompt(
        self,
        modality: str,
        label: str,
        deepfake_score: float,
        confidence: float,
        indicators: list[str],
        details: dict[str, float],
    ) -> str:
        indicator_text = "; ".join(indicators) if indicators else "No indicators"
        details_text = "; ".join([f"{k}={v}" for k, v in details.items()]) if details else "No details"
        return (
            "You are an AI cybersecurity analyst. "
            "Write a precise deepfake assessment in exactly 3 concise sentences. "
            "Sentence 1: risk interpretation with score/confidence. "
            "Sentence 2: reference at least two numeric forensic metrics from details. "
            "Sentence 3: practical verification step. "
            "Do not claim certainty and avoid hype. "
            f"Modality: {modality}. "
            f"Label: {label}. "
            f"Deepfake score: {deepfake_score:.2f}. "
            f"Confidence: {confidence:.2f}. "
            f"Indicators: {indicator_text}. "
            f"Forensic details: {details_text}."
        )


def build_local_summary(
    modality: str,
    label: str,
    deepfake_score: float,
    confidence: float,
    indicators: list[str],
    details: dict[str, float],
) -> str:
    score_pct = round(deepfake_score * 100)
    conf_pct = round(confidence * 100)
    strength = "strong" if score_pct >= 75 else "moderate" if score_pct >= 55 else "low"
    conf_band = "high" if conf_pct >= 75 else "medium" if conf_pct >= 55 else "limited"

    metric_preview = ", ".join([f"{k}={v}" for k, v in list(details.items())[:3]])
    if not metric_preview:
        metric_preview = "no numeric forensic metrics available"

    if label == "Suspected Deepfake":
        return (
            f"{modality.title()} analysis indicates {strength} manipulation risk at {score_pct}% deepfake score with {conf_pct}% confidence. "
            f"Key forensic metrics: {metric_preview}. "
            "Verify source provenance and compare with trusted originals before acceptance."
        )

    indicator_count = len(indicators)
    return (
        f"{modality.title()} analysis currently indicates likely authentic media with {conf_band} confidence "
        f"({score_pct}% deepfake score, {indicator_count} indicator(s) reviewed). "
        f"Key forensic metrics: {metric_preview}. "
        "For high-impact decisions, keep secondary verification in place."
    )
