from pathlib import Path
import subprocess
from typing import Iterator
from .config import SETTINGS

class Rclone:
    def __init__(self, mount_path: Path | None = None):
        self.mount = Path(mount_path or SETTINGS.google_photos_mount)

    def iter_media(self, max_scan: int = 2000) -> Iterator[Path]:
        # Prefer recent years to reduce initial scan overhead on large mounts
        candidates: list[Path] = []
        media_root = self.mount / "media"
        by_year = media_root / "by-year"
        recent_years = []
        try:
            from datetime import datetime
            y = datetime.now().year
            recent_years = [str(y), str(y-1), str(y-2)]
        except Exception:
            recent_years = []
        for y in recent_years:
            candidates.append(by_year / y)
        # Fallback to media/all if needed
        candidates.append(media_root / "all")

        seen = 0
        for base in candidates:
            if not base.exists():
                continue
            for p in base.rglob("*"):
                if seen >= max_scan:
                    return
                if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".heic", ".mp4", ".mov", ".avi", ".mkv"}:
                    seen += 1
                    yield p

    def download(self, src: Path, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Copy via local file system since it's a mount
        subprocess.run(["/bin/cp", "-f", str(src), str(dest)], check=True)

    def upload(self, src: Path, dest_rel: Path) -> None:
        # Place in processed_dir first; user runs rclone upload separately if desired.
        pass

