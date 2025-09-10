from pathlib import Path
from typing import Optional
from datetime import datetime
import shutil
from .config import SETTINGS
from .db import DB, sha256_file
from .rclone_integration import Rclone
from .processing.processors import PhotoProcessor, VideoProcessor
from .storage import StorageManager

class Organizer:
    def __init__(self):
        self.db = DB(SETTINGS.db_path)
        self.rclone = Rclone()
        self.storage = StorageManager()
        self.photo = PhotoProcessor()
        self.video = VideoProcessor()

    def organize_rel_path(self, src: Path) -> Path:
        # Use date-based folders YYYY/MM/DD and keep original name
        try:
            ts = datetime.fromtimestamp(src.stat().st_mtime)
        except Exception:
            ts = datetime.now()
        return Path(f"{ts:%Y/%m/%d}") / src.name

    def process_one(self, src: Path) -> Optional[Path]:
        rel = self.organize_rel_path(src)
        staged = SETTINGS.raw_dir / rel
        out = SETTINGS.processed_dir / rel
        if out.exists():
            return None

        # Pre-check disk budget: assume up to 2x size during processing
        size = src.stat().st_size
        need = int(size * 2.5)
        if not self.storage.ensure_room(need):
            return None

        # Download
        self.rclone.download(src, staged)
        h = sha256_file(staged)
        if self.db.has_hash(h):
            staged.unlink(missing_ok=True)
            return None

        out.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() in {".jpg", ".jpeg", ".png", ".heic"}:
            self.photo.enhance(staged, out.with_suffix(".jpg"))
            final_out = out.with_suffix(".jpg")
            media_type = "photo"
        else:
            self.video.enhance(staged, out.with_suffix(".mp4"))
            final_out = out.with_suffix(".mp4")
            media_type = "video"

        # Cleanup staged file to reclaim space
        staged.unlink(missing_ok=True)

        # Record
        self.db.add(str(rel), h, media_type)
        return final_out

    def run_once(self, limit: int = 20) -> int:
        count = 0
        for p in self.rclone.iter_media():
            if count >= limit:
                break
            out = self.process_one(p)
            if out:
                count += 1
        return count

