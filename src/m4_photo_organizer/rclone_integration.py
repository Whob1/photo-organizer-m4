from pathlib import Path
import subprocess
from typing import Iterator, List
import os, time
from collections import deque
from .config import SETTINGS

SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".mp4", ".mov", ".avi", ".mkv"}

class Rclone:
    def __init__(self, mount_path: Path | None = None):
        self.mount = Path(mount_path or SETTINGS.google_photos_mount)

    def _bfs_scandir(self, root: Path, max_entries: int, max_seconds: int) -> Iterator[Path]:
        start = time.time()
        q: deque[Path] = deque([root])
        yielded = 0
        while q:
            if yielded >= max_entries or (time.time() - start) > max_seconds:
                return
            d = q.popleft()
            try:
                with os.scandir(d) as it:
                    for entry in it:
                        if yielded >= max_entries or (time.time() - start) > max_seconds:
                            return
                        name = entry.name
                        if name.startswith('.'):
                            continue
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                q.append(Path(entry.path))
                            elif entry.is_file(follow_symlinks=False):
                                if Path(name).suffix.lower() in SUFFIXES:
                                    yielded += 1
                                    yield Path(entry.path)
                        except PermissionError:
                            continue
            except (FileNotFoundError, NotADirectoryError, PermissionError):
                continue

    def _mdfind_media(self, max_scan: int, src_dir: Path | None) -> Iterator[Path]:
        # Use macOS Spotlight (mdfind) to quickly locate images/movies under the mount
        try:
            import platform, subprocess
            if platform.system() != "Darwin":
                return iter(())
            base = str(src_dir or self.mount)
            query = '(kMDItemContentTypeTree == "public.image" || kMDItemContentTypeTree == "public.movie")'
            cmd = [
                "mdfind",
                "-onlyin", base,
                query,
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=SETTINGS.scan_max_seconds)
            if res.returncode != 0:
                return iter(())
            lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
            out: list[Path] = []
            for p in lines:
                if len(out) >= max_scan:
                    break
                suf = Path(p).suffix.lower()
                if suf in SUFFIXES:
                    out.append(Path(p))
            return iter(out)
        except Exception:
            return iter(())

    def iter_media(self, max_scan: int = 2000, src_dir: Path | None = None) -> Iterator[Path]:
        # Try fast mdfind first on macOS
        fast = list(self._mdfind_media(max_scan, src_dir))
        if fast:
            for p in fast:
                yield p
            return
        # Build candidate roots
        media_root = self.mount / "media"
        candidates: List[Path] = []
        if src_dir:
            candidates.append(Path(src_dir))
        else:
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
        # Walk each root with bounded time and entries
        per_root = min(max_scan, SETTINGS.scan_max_entries_per_root)
        max_sec = SETTINGS.scan_max_seconds
        seen = 0
        for base in candidates:
            if not base.exists():
                continue
            for p in self._bfs_scandir(base, per_root, max_sec):
                yield p
                seen += 1
                if seen >= max_scan:
                    return

    def download(self, src: Path, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Copy via local file system since it's a mount
        subprocess.run(["/bin/cp", "-f", str(src), str(dest)], check=True)

    def upload(self, src: Path, dest_rel: Path) -> None:
        # Place in processed_dir first; user runs rclone upload separately if desired.
        pass

