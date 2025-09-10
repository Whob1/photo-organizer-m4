import subprocess
from pathlib import Path
from typing import Optional
from .config import SETTINGS

class Uploader:
    def __init__(self):
        self.mount = SETTINGS.google_photos_mount

    def upload(self, local_file: Path, dest_rel: Path) -> None:
        # Since Google Photos via rclone is mounted read-write depending on config, we attempt copy.
        # If mount is read-only, this will fail and you can switch to rclone copy with a remote.
        dest = Path(self.mount) / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["/bin/cp", "-f", str(local_file), str(dest)], check=True)

