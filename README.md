# Multimodal Deepfake Detector (Hackathon Starter)

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
- Deepfake score (`0.0 - 1.0`)
- Confidence score (`0.0 - 1.0`)
- Indicators explaining why media was flagged

## 1) Quick Start

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run API

```bash
uvicorn app.main:app --reload
```

API docs:

- http://127.0.0.1:8000/docs

Web pages:

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/live
- http://127.0.0.1:8000/about

## 2) API Usage

### Analyze media file

`POST /analyze`

Form fields:

- `file`: media file upload
- `modality` (optional): `image | audio | video` (auto-detect by extension/content-type if omitted)

Example with curl:

```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -F "file=@sample.mp4"
```

### Analyze single camera frame

`POST /analyze-frame`

Form fields:

- `file`: frame image (jpg/png)

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

## 7) Folder Structure

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
