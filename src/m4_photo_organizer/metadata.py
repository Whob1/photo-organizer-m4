import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import exifread
from PIL import Image
import piexif

@dataclass
class MediaMetadata:
    taken_at: datetime
    camera_make: Optional[str]
    camera_model: Optional[str]
    width: Optional[int]
    height: Optional[int]


def _exifread_dt_to_datetime(tag) -> Optional[datetime]:
    try:
        # Format like '2020:07:15 12:34:56'
        return datetime.strptime(str(tag), "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None


def extract_photo_metadata(path: Path) -> MediaMetadata:
    taken = None
    make = None
    model = None
    width = None
    height = None

    try:
        with path.open("rb") as f:
            tags = exifread.process_file(f, details=False)
            taken = _exifread_dt_to_datetime(tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime"))
            make = str(tags.get("Image Make")) if tags.get("Image Make") else None
            model = str(tags.get("Image Model")) if tags.get("Image Model") else None
    except Exception:
        pass

    try:
        with Image.open(path) as im:
            width, height = im.size
    except Exception:
        pass

    if taken is None:
        # Fallback to file modified time
        taken = datetime.fromtimestamp(path.stat().st_mtime)

    return MediaMetadata(taken_at=taken, camera_make=make, camera_model=model, width=width, height=height)


def write_sidecar_json(path: Path, meta: MediaMetadata) -> None:
    out = path.with_suffix(path.suffix + ".json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        json.dump({
            "taken_at": meta.taken_at.isoformat(),
            "camera_make": meta.camera_make,
            "camera_model": meta.camera_model,
            "width": meta.width,
            "height": meta.height,
        }, f, indent=2)

