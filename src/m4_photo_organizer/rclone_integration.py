from pathlib import Path
import subprocess
from typing import Iterator
from .config import SETTINGS

class Rclone:
    def __init__(self, mount_path: Path | None = None):
        self.mount = Path(mount_path or SETTINGS.google_photos_mount)

    def iter_media(self) -> Iterator[Path]:
        # Walk the rclone mount and yield files
        for p in self.mount.rglob("*"):
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".heic", ".mp4", ".mov", ".avi", ".mkv"}:
                yield p

    def download(self, src: Path, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Copy via local file system since it's a mount
        subprocess.run(["/bin/cp", "-f", str(src), str(dest)], check=True)

    def upload(self, src: Path, dest_rel: Path) -> None:
        # Place in processed_dir first; user runs rclone upload separately if desired.
        pass

