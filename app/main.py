from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.detectors.audio_detector import AudioDetector
from app.detectors.image_detector import ImageDetector
from app.detectors.video_detector import VideoDetector
from app.schemas import DetectionResult, HealthResponse

app = FastAPI(title="Multimodal Deepfake Detector", version="0.1.0")

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "web"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

image_detector = ImageDetector()
audio_detector = AudioDetector()
video_detector = VideoDetector()

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/live")
def live() -> FileResponse:
    return FileResponse(STATIC_DIR / "live.html")


@app.get("/about")
def about() -> FileResponse:
    return FileResponse(STATIC_DIR / "about.html")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/analyze", response_model=DetectionResult)
async def analyze_media(
    file: UploadFile = File(...),
    modality: Literal["image", "audio", "video"] | None = None,
) -> DetectionResult:
    media_bytes = await file.read()
    if not media_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    inferred = modality or infer_modality(file.filename, file.content_type)
    if inferred is None:
        raise HTTPException(
            status_code=400,
            detail="Could not infer modality. Set modality explicitly to image, audio, or video.",
        )

    if inferred == "image":
        out = image_detector.analyze(media_bytes)
    elif inferred == "audio":
        out = audio_detector.analyze(media_bytes)
    else:
        out = video_detector.analyze(media_bytes)

    return DetectionResult(
        modality=out.modality,
        label=out.label,
        deepfake_score=out.deepfake_score,
        confidence=out.confidence,
        indicators=out.indicators,
    )


@app.post("/analyze-frame", response_model=DetectionResult)
async def analyze_frame(file: UploadFile = File(...)) -> DetectionResult:
    """Analyze a single image frame from live webcam input."""
    media_bytes = await file.read()
    if not media_bytes:
        raise HTTPException(status_code=400, detail="Uploaded frame is empty")

    out = image_detector.analyze(media_bytes)
    return DetectionResult(
        modality=out.modality,
        label=out.label,
        deepfake_score=out.deepfake_score,
        confidence=out.confidence,
        indicators=out.indicators,
    )


def infer_modality(filename: str | None, content_type: str | None) -> Literal["image", "audio", "video"] | None:
    if content_type:
        lower_type = content_type.lower()
        if lower_type.startswith("image/"):
            return "image"
        if lower_type.startswith("audio/"):
            return "audio"
        if lower_type.startswith("video/"):
            return "video"

    if filename:
        ext = Path(filename).suffix.lower()
        if ext in IMAGE_EXTS:
            return "image"
        if ext in AUDIO_EXTS:
            return "audio"
        if ext in VIDEO_EXTS:
            return "video"

    return None
