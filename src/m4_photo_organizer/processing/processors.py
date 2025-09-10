from pathlib import Path
from typing import Optional
from PIL import Image
import subprocess

class PhotoProcessor:
    def enhance(self, src: Path, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as im:
            im = im.convert("RGB")
            im.save(dest, quality=92, optimize=True)

class VideoProcessor:
    def enhance(self, src: Path, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Simple re-encode placeholder using ffmpeg if available
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k",
            str(dest),
        ]
        subprocess.run(cmd, check=True)

