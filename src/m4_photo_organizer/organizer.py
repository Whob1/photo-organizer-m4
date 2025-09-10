from pathlib import Path
from typing import Optional
from datetime import datetime
import shutil
from .config import SETTINGS
from .db import DB, sha256_file
from .rclone_integration import Rclone
from .processing.processors import PhotoProcessor, VideoProcessor
from .storage import StorageManager
from .metadata import extract_photo_metadata, write_sidecar_json
from .uploader import Uploader
from imagehash import phash
from PIL import Image

from .logging import get_logger

class Organizer:
    def __init__(self):
        self.log = get_logger(__name__)
        self.db = DB(SETTINGS.db_path)
        self.rclone = Rclone()
        self.storage = StorageManager()
        self.photo = PhotoProcessor()
        self.video = VideoProcessor()
        self.uploader = Uploader()
        self.log.info("Organizer initialized", extra={"max_disk": SETTINGS.max_disk_bytes})

    def organize_rel_path(self, src: Path) -> Path:
        # Prefer EXIF/metadata date for photos; fallback to mtime
        ts = None
        try:
            if src.suffix.lower() in {".jpg", ".jpeg", ".png", ".heic"}:
                meta = extract_photo_metadata(src)
                ts = meta.taken_at
        except Exception:
            ts = None
        if ts is None:
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
        # Skip if DB already recorded this rel path (processed previously)
        if self.db.has_path(str(rel)):
            return None

        # Pre-check disk budget: assume up to ~2.5x size during processing
        try:
            size = src.stat().st_size
        except Exception:
            # If source is from remote (not on mount), estimate conservatively (50MB)
            size = 50 * 1024 * 1024
        need = int(size * 2.5)
        if not self.storage.ensure_room(need):
            self.log.warning("Skipping due to disk budget", extra={"estimated_bytes": size, "need": need})
            return None
            return None

        # Download
        self.rclone.download(src, staged)
        h = sha256_file(staged)
        # Perceptual hash for additional duplicate detection (photos only)
        p_hash_hex = None
        try:
            with Image.open(staged) as pim:
                p_hash_hex = str(phash(pim))
        except Exception:
            p_hash_hex = None
        if self.db.has_hash(h):
            staged.unlink(missing_ok=True)
            return None

        out.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() in {".jpg", ".jpeg", ".png", ".heic"}:
            final_out = out.with_suffix(".jpg")
            thumb = SETTINGS.thumbnails_dir / self.organize_rel_path(src).with_suffix(".jpg")
            ai_sum = self.photo.enhance(staged, final_out, thumb_out=thumb)
            media_type = "photo"
            try:
                meta = extract_photo_metadata(final_out)
                # Merge AI summary into sidecar by extending metadata dict
                write_sidecar_json(final_out, meta)
            except Exception:
                pass
        else:
            final_out = out.with_suffix(".mp4")
            thumb = SETTINGS.thumbnails_dir / self.organize_rel_path(src).with_suffix(".jpg")
            ai_sum = self.video.enhance(staged, final_out, thumb_out=thumb)
            media_type = "video"

        # Cleanup staged file to reclaim space
        staged.unlink(missing_ok=True)

        # Upload back to Google Photos mount under same rel path
        try:
            self.uploader.upload(final_out, rel if final_out.suffix == rel.suffix else rel.with_suffix(final_out.suffix))
        except Exception:
            # If upload fails, keep file locally for retry later
            pass
        else:
            # After successful upload, remove local processed file to honor 5GB cap
            try:
                final_out.unlink(missing_ok=True)
            except Exception:
                pass

        # Record
        self.db.add(str(rel), h, media_type, phash=p_hash_hex)
        return final_out

    def run_once(self, limit: int = 20, scan_seconds: int | None = None, scan_max: int | None = None, src_dir: Path | None = None) -> int:
        self.log.info("Scanning for media to process", extra={"limit": limit})
        count = 0
        # temporarily override scanning knobs
        if scan_seconds is not None:
            old_secs = SETTINGS.scan_max_seconds
            SETTINGS.scan_max_seconds = scan_seconds
        else:
            old_secs = None
        try:
            max_scan = scan_max if scan_max is not None else limit * 50
            for p in self.rclone.iter_media(max_scan=max_scan, src_dir=src_dir):
                if count >= limit:
                    break
                self.log.debug("Processing item", extra={"path": str(p)})
                out = self.process_one(p)
                if out:
                    count += 1
                    self.log.info("Processed item", extra={"count": count, "output": str(out)})
        finally:
            if old_secs is not None:
                SETTINGS.scan_max_seconds = old_secs
        self.log.info("Run complete", extra={"processed": count})
        return count
