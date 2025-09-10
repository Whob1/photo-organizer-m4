# m4-photo-organizer

Automatic photo and video organizer and enhancer for Apple M4.

Key features:
- Sources from rclone-mounted Google Photos at /Users/sheldon/GooglePhotos
- Streams items for processing, keeping local disk use under 5 GB
- Enhances photos/videos, organizes by date/location/content
- Uploads processed items back to Google Photos
- Tracks processed items to avoid duplicates

Quick start
- Ensure rclone mount is available at /Users/sheldon/GooglePhotos
- Python 3.11+ recommended

Install deps (optional – you can use your preferred tool)
```
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

CLI
```
photoorg run --help
```

Recommended way to run (auto-creates venv, installs deps, sets Apple Silicon hints):
```
scripts/run.zsh setup
scripts/run.zsh run --limit 5
scripts/run.zsh status
```

AI features
- Photo enhancement: ONNX photo model (ESRGAN x2 by default) with fallback to fast local pipeline
- Video enhancement: frame-wise sampling with AI metrics; hook for ONNX model (downloaded if present)
- Face detection (OpenCV Haar); face count and bounding boxes (limited in sidecar)
- Quality scoring: blur, brightness, colorfulness; tags like blurry/low_light/vivid
- Perceptual de-duplication: pHash stored alongside SHA-256
- Thumbnails: generated at data/thumbnails

Models
- Models are stored under models/ and are downloaded automatically on first run.
- Defaults (override via env):
  - PHOTOORG_PHOTO_MODEL_URL: ESRGAN x2 ONNX
  - PHOTOORG_VIDEO_MODEL_URL: SRMD x2 ONNX
- To change paths: PHOTOORG_MODELS_DIR, PHOTOORG_PHOTO_MODEL_NAME, PHOTOORG_VIDEO_MODEL_NAME

Configuration flags (env)
- PHOTOORG_AI_FACES=0 to disable face detection
- PHOTOORG_AI_CLASSIFY=0 to disable quality scoring/tags
- PHOTOORG_AI_ENHANCE=0 to disable enhancement

Directories
- data/raw: staging downloads
- data/processed: processed output ready to upload
- data/tmp: scratch space

Config
See src/m4_photo_organizer/config.py for defaults. You can override with env vars or a TOML file.

