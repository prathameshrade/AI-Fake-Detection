# Multimodal Deepfake Detector

This project provides a practical baseline for detecting potentially manipulated media across:

- Images
- Audio
- Video

It also includes a unique multi-page web interface:

- Upload Lab (`/`) for file-based analysis
- Live Camera (`/live`) for front-camera frame analysis
- Method (`/about`) for concise technical overview

It returns:

- Authenticity label (`Real` or `Suspected Deepfake`)
- Risk level (`Low | Medium | High | Critical`)
- Deepfake score (`0.0 - 1.0`)
- Confidence score (`0.0 - 1.0`)
- Indicators explaining why media was flagged
- Forensic detail metrics (modality-specific numeric signals)
- Automatic Google AI summary (falls back to local summary if unavailable)

## 1) Quick Start

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run API

```bash
uvicorn app.main:app --reload
```

### Optional: Enable Google AI summaries

Set a Google API key before starting the server.

PowerShell:

```powershell
$env:GOOGLE_API_KEY="your_google_api_key"
```

Optional model override:

```powershell
$env:GOOGLE_MODEL="gemini-1.5-flash-latest"
```

Google key configuration is hidden from frontend UI.

- Set `GOOGLE_API_KEY` in server environment variables.
- Frontend does not display or store API keys.
- Backend keeps key handling server-side.

API docs:

- http://127.0.0.1:8000/docs

Web pages:

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/live
- http://127.0.0.1:8000/about

Usage tracking endpoint:

- http://127.0.0.1:8000/admin/usage

## 2) API Usage

### Analyze media file

`POST /analyze`

Form fields:

- `file`: media file upload
- `modality` (optional): `image | audio | video` (auto-detect by extension/content-type if omitted)
- `use_google` (optional): `true | false` (default `true`)
- `google_api_key` (optional): request-scoped API key sent by UI/clients

Response adds:

- `risk_level`
- `forensic_details`
- `analysis_summary`
- `analysis_source`

Example with curl:

```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -F "file=@sample.mp4"
```

### Analyze single camera frame

`POST /analyze-frame`

Form fields:

- `file`: frame image (jpg/png)
- `use_google` (optional): `true | false` (default `false`, disabled by default in live UI for performance)
- `google_api_key` (optional): request-scoped API key sent by UI/clients

## 3) How It Works

This starter uses explainable signal/artifact heuristics rather than a heavy deep model.

- Image detector:
  - Blur / over-smoothing checks
  - High-frequency noise and texture consistency
  - Compression and edge artifact signals
- Audio detector:
  - Spectral flatness and high-frequency energy profile
  - Zero-crossing and short-time feature stability
  - Harmonic/noise ratio cues
- Video detector:
  - Per-frame image analysis on sampled frames
  - Temporal inconsistency and flicker checks
  - Aggregation across frame-level scores

## 4) Hackathon Upgrade Path (High Impact)

To improve accuracy quickly, add one lightweight model per modality and fuse with heuristics:

- Image: EfficientNet / Xception finetuned on FaceForensics++ or DFDC frames
- Audio: wav2vec2 or CNN over mel-spectrogram for fake speech
- Video: temporal transformer or frame+optical-flow fusion

Recommended fusion:

- Final score = `0.5 * model_score + 0.5 * heuristic_score`
- Calibrate confidence using validation set reliability plots

## 5) Suggested Datasets

- Images/Video: FaceForensics++, Celeb-DF, DFDC
- Audio: ASVspoof, Fake-or-Real speech datasets

## 6) Limitations (Current Starter)

- Heuristics are explainable and fast but less accurate than trained detectors.
- Best suited as a baseline or fallback when model inference is unavailable.
- Google summary generation is optional and depends on API key/network availability.

## 7) Visitor Usage Database

The backend stores visitor events in SQLite at:

- `app/data/usage.db`

Captured fields include:

- IP address
- path/method/status
- user agent
- inferred OS/browser
- client-reported system name (best effort from browser platform data)
- page path

Get recent events:

```bash
curl "http://127.0.0.1:8000/admin/usage?limit=100"
```

Important:

- Browser security does not expose an exact host/computer name; `system_name` is best-effort platform info.
- Ensure legal notice/consent is added before production use.

## 8) Mobile Optimization

The application is fully optimized for mobile devices with:

### Responsive Design

- **Mobile-first approach**: Breakpoints at 860px (tablets) and 480px (phones)
- **Adaptive layouts**: Single-column layouts on phones, multi-column on larger screens
- **Touch-friendly UI**: 44px minimum touch target sizes per WCAG guidelines
- **Safe area handling**: Proper support for notched devices (notch-safe viewport)

### Mobile Features

- **Live camera on mobile**: Front-facing camera with orientation handling
- **Touch interactions**: Visual feedback on button presses and form inputs
- **Performance**: Request timeout (15s) for slower mobile networks
- **Accessibility**: Improved input handling, keyboard behaviors, and focus management

### Browser Support

- iOS Safari (15+): Full support with home screen app capability
- Android Chrome (90+): Full support with progressive features
- Mobile Firefox: Supported
- Samsung Internet: Supported

### Files

- `web/mobile-helper.js`: Centralized mobile enhancements (safe area, keyboard, zoom handling)
- `web/styles.css`: Comprehensive media queries for mobile/tablet/desktop
- `web/app.js`: Double-submit prevention, touch feedback
- `web/live.js`: Camera permission handling, orientation awareness

## 9) Folder Structure

```text
app/
  main.py
  schemas.py
  detectors/
    base.py
    image_detector.py
    audio_detector.py
    video_detector.py
```
