from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.detectors.audio_detector import AudioDetector
from app.detectors.image_detector import ImageDetector
from app.detectors.video_detector import VideoDetector
from app.schemas import DetectionResult, HealthResponse
from app.services.google_analysis import GoogleAnalysisClient, build_local_summary
from app.services.usage_db import UsageDB, parse_browser_from_user_agent, parse_os_from_user_agent

app = FastAPI(title="Multimodal Deepfake Detector", version="0.1.0")

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "web"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

image_detector = ImageDetector()
audio_detector = AudioDetector()
video_detector = VideoDetector()
google_client = GoogleAnalysisClient()
usage_db = UsageDB(BASE_DIR / "app" / "data" / "usage.db")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
MAX_FRAME_BYTES = 6 * 1024 * 1024


@app.on_event("startup")
def init_usage_database() -> None:
    usage_db.init()


@app.middleware("http")
async def log_visitor_request(request: Request, call_next):
    response = await call_next(request)
    try:
        ip_address = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        usage_db.log_event(
            {
                "event_type": "request",
                "ip_address": ip_address,
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "user_agent": user_agent,
                "os_name": request.headers.get("x-client-os") or parse_os_from_user_agent(user_agent),
                "system_name": request.headers.get("x-client-system") or "Unknown",
                "browser_name": request.headers.get("x-client-browser") or parse_browser_from_user_agent(user_agent),
                "accept_language": request.headers.get("accept-language"),
                "page": request.headers.get("x-page-path"),
            }
        )
    except Exception:
        # Do not block user requests on telemetry failures.
        pass
    return response


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


@app.post("/telemetry/client")
async def log_client_telemetry(
    request: Request,
    system_name: str | None = Form(default=None),
    os_name: str | None = Form(default=None),
    browser_name: str | None = Form(default=None),
    page: str | None = Form(default=None),
) -> dict[str, str]:
    user_agent = request.headers.get("user-agent", "")
    usage_db.log_event(
        {
            "event_type": "client_telemetry",
            "ip_address": get_client_ip(request),
            "path": request.url.path,
            "method": request.method,
            "status_code": 200,
            "user_agent": user_agent,
            "os_name": os_name or parse_os_from_user_agent(user_agent),
            "system_name": system_name or "Unknown",
            "browser_name": browser_name or parse_browser_from_user_agent(user_agent),
            "accept_language": request.headers.get("accept-language"),
            "page": page,
        }
    )
    return {"status": "logged"}


@app.get("/admin/usage")
def recent_usage(limit: int = 200) -> list[dict[str, str | int | None]]:
    safe_limit = max(1, min(limit, 1000))
    return usage_db.recent_events(limit=safe_limit)


@app.post("/analyze", response_model=DetectionResult)
async def analyze_media(
    file: UploadFile = File(...),
    modality: Literal["image", "audio", "video"] | None = None,
    google_api_key: str | None = Form(default=None),
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

    analysis_summary, analysis_source = summarize_with_optional_google(
        modality=out.modality,
        label=out.label,
        deepfake_score=out.deepfake_score,
        confidence=out.confidence,
        indicators=out.indicators,
        use_google=True,
        google_api_key=google_api_key,
        details=out.details,
    )

    return DetectionResult(
        modality=out.modality,
        label=out.label,
        risk_level=calculate_risk_level(out.deepfake_score, out.confidence),
        deepfake_score=out.deepfake_score,
        confidence=out.confidence,
        indicators=out.indicators,
        forensic_details=out.details,
        analysis_summary=analysis_summary,
        analysis_source=analysis_source,
    )


@app.post("/analyze-frame", response_model=DetectionResult)
async def analyze_frame(
    file: UploadFile = File(...),
    google_api_key: str | None = Form(default=None),
) -> DetectionResult:
    """Analyze a single image frame from live webcam input."""
    if not is_image_upload(file.filename, file.content_type):
        raise HTTPException(status_code=400, detail="Frame endpoint accepts image files only")

    media_bytes = await file.read()
    if not media_bytes:
        raise HTTPException(status_code=400, detail="Uploaded frame is empty")
    if len(media_bytes) > MAX_FRAME_BYTES:
        raise HTTPException(status_code=413, detail="Frame file too large (max 6 MB)")

    out = image_detector.analyze(media_bytes)
    analysis_summary, analysis_source = summarize_with_optional_google(
        modality=out.modality,
        label=out.label,
        deepfake_score=out.deepfake_score,
        confidence=out.confidence,
        indicators=out.indicators,
        use_google=True,
        google_api_key=google_api_key,
        details=out.details,
    )

    return DetectionResult(
        modality=out.modality,
        label=out.label,
        risk_level=calculate_risk_level(out.deepfake_score, out.confidence),
        deepfake_score=out.deepfake_score,
        confidence=out.confidence,
        indicators=out.indicators,
        forensic_details=out.details,
        analysis_summary=analysis_summary,
        analysis_source=analysis_source,
    )


def summarize_with_optional_google(
    modality: str,
    label: str,
    deepfake_score: float,
    confidence: float,
    indicators: list[str],
    use_google: bool,
    google_api_key: str | None,
    details: dict[str, float],
) -> tuple[str, Literal["google", "local"]]:
    local_summary = build_local_summary(
        modality=modality,
        label=label,
        deepfake_score=deepfake_score,
        confidence=confidence,
        indicators=indicators,
        details=details,
    )

    if not use_google:
        return local_summary, "local"

    request_key = (google_api_key or "").strip()
    client = GoogleAnalysisClient(api_key=request_key) if request_key else google_client
    google_summary = client.summarize_result(
        modality=modality,
        label=label,
        deepfake_score=deepfake_score,
        confidence=confidence,
        indicators=indicators,
        details=details,
    )
    if google_summary:
        return google_summary, "google"
    return local_summary, "local"


def calculate_risk_level(deepfake_score: float, confidence: float) -> Literal["Low", "Medium", "High", "Critical"]:
    weighted = (0.75 * deepfake_score) + (0.25 * confidence)
    if weighted >= 0.82:
        return "Critical"
    if weighted >= 0.67:
        return "High"
    if weighted >= 0.5:
        return "Medium"
    return "Low"


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


def is_image_upload(filename: str | None, content_type: str | None) -> bool:
    if content_type and content_type.lower().startswith("image/"):
        return True
    if filename:
        return Path(filename).suffix.lower() in IMAGE_EXTS
    return False


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"
