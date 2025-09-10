from pathlib import Path
import subprocess
from typing import Iterator
from .config import SETTINGS

class Rclone:
    def __init__(self, mount_path: Path | None = None):
        self.mount = Path(mount_path or SETTINGS.google_photos_mount)

    def iter_media(self, max_scan: int = 2000) -> Iterator[Path]:
        # Scan only media files with known extensions, across common mount dirs
        suffixes = {".jpg", ".jpeg", ".png", ".heic", ".mp4", ".mov", ".avi", ".mkv"}
        candidates: list[Path] = []
        media_root = self.mount / "media"
        # Prioritize by-year recent, then by-month/day, then all, then albums
        try:
            from datetime import datetime
            y = datetime.now().year
            recent = [str(y), str(y-1), str(y-2)]
        except Exception:
            recent = []
        by_year = media_root / "by-year"
        for yy in recent:
            candidates.append(by_year / yy)
        candidates.extend([
            media_root / "by-month",
            media_root / "by-day",
            media_root / "all",
            self.mount / "album",
            self.mount / "shared-album",
        ])
        seen = 0
        for base in candidates:
            if not base.exists():
                continue
            try:
                for p in base.rglob("*"):
                    if seen >= max_scan:
                        return
                    if p.is_file() and p.suffix.lower() in suffixes:
                        seen += 1
                        yield p
            except Exception:
                # Ignore unreadable paths
                continue

    def download(self, src: Path, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Copy via local file system since it's a mount
        subprocess.run(["/bin/cp", "-f", str(src), str(dest)], check=True)

    def upload(self, src: Path, dest_rel: Path) -> None:
        # Place in processed_dir first; user runs rclone upload separately if desired.
        pass

