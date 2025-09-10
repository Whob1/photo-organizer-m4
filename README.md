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

Directories
- data/raw: staging downloads
- data/processed: processed output ready to upload
- data/tmp: scratch space

Config
See src/m4_photo_organizer/config.py for defaults. You can override with env vars or a TOML file.

