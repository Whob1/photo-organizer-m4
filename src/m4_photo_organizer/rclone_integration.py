from pathlib import Path
import subprocess
from typing import Iterator, List
import os, time
from collections import deque
from .config import SETTINGS
from .logging import get_logger

SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".mp4", ".mov", ".avi", ".mkv", ".webp", ".gif", ".tiff", ".tif", ".bmp", ".webm", ".m4v", ".3gp", ".flv", ".wmv"}

class Rclone:
    def __init__(self, mount_path: Path | None = None):
        self.mount = Path(mount_path or SETTINGS.google_photos_mount)
        self._remote_map: dict[Path, str | None] = {}
        self.log = get_logger(__name__)

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

    def _lsf_media(self, max_scan: int) -> list[tuple[Path, str]]:
        try:
            import subprocess
            remote = SETTINGS.rclone_remote
            prefixes = ["", "media", "media/by-year", "album", "shared-album"]
            out: list[tuple[Path, str]] = []
            for pref in prefixes:
                if len(out) >= max_scan:
                    break
                target = remote if not pref else f"{remote}{pref}"
                cmd = ["rclone", "lsf", target, "--recursive", "--files-only"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=max(SETTINGS.lsf_timeout_seconds, 15))
                if res.returncode != 0:
                    continue
                for line in res.stdout.splitlines():
                    rel = line.strip()
                    if not rel or rel.endswith("/"):
                        continue
                    rel_path = rel if not pref else f"{pref}/{rel}"
                    suf = Path(rel_path).suffix.lower()
                    if suf in SUFFIXES:
                        mount_path = self.mount / rel_path
                        out.append((mount_path, rel_path))
                        if len(out) >= max_scan:
                            break
            return out
        except Exception:
            return []

    def _find_media_recursive(self, root: Path, max_entries: int, max_seconds: int) -> Iterator[Path]:
        """Enhanced recursive search with better error handling and logging."""
        start = time.time()
        found = 0
        self.log.debug(f"Starting recursive search in {root}")
        
        if not root.exists():
            self.log.warning(f"Search root does not exist: {root}")
            return
            
        if not root.is_dir():
            self.log.warning(f"Search root is not a directory: {root}")
            return
            
        try:
            for item in root.rglob("*"):
                if found >= max_entries or (time.time() - start) > max_seconds:
                    self.log.debug(f"Search limits reached: found={found}, time={time.time()-start:.1f}s")
                    return
                    
                if item.is_file() and not item.name.startswith('.'):
                    suffix = item.suffix.lower()
                    if suffix in SUFFIXES:
                        found += 1
                        self.log.debug(f"Found media file: {item}")
                        yield item
                        
        except (PermissionError, OSError) as e:
            self.log.warning(f"Error during recursive search in {root}: {e}")
            
        self.log.debug(f"Recursive search completed: found {found} files in {time.time()-start:.1f}s")

    def _search_common_directories(self, max_scan: int) -> Iterator[Path]:
        """Search common photo/video directories on the system."""
        common_dirs = [
            Path.home() / "Pictures",
            Path.home() / "Downloads", 
            Path.home() / "Desktop",
            Path("/tmp"),
            Path("/var/tmp"),
            Path.cwd(),
        ]
        
        # Add environment variable paths
        if "PHOTOORG_SEARCH_DIRS" in os.environ:
            extra_dirs = os.environ["PHOTOORG_SEARCH_DIRS"].split(":")
            common_dirs.extend([Path(d) for d in extra_dirs if d.strip()])
            
        found = 0
        for search_dir in common_dirs:
            if found >= max_scan:
                break
                
            if search_dir.exists() and search_dir.is_dir():
                self.log.debug(f"Searching common directory: {search_dir}")
                try:
                    for item in self._find_media_recursive(search_dir, max_scan - found, SETTINGS.scan_max_seconds):
                        yield item
                        found += 1
                        if found >= max_scan:
                            break
                except Exception as e:
                    self.log.warning(f"Error searching {search_dir}: {e}")
                    continue

    def iter_media(self, max_scan: int = 2000, src_dir: Path | None = None) -> Iterator[Path]:
        """Enhanced media discovery with comprehensive fallback mechanisms."""
        self.log.info(f"Starting media search: max_scan={max_scan}, src_dir={src_dir}")
        found_count = 0
        
        # If specific source directory is provided, search there first
        if src_dir:
            src_path = Path(src_dir)
            self.log.info(f"Searching specified directory: {src_path}")
            if src_path.exists():
                for item in self._find_media_recursive(src_path, max_scan, SETTINGS.scan_max_seconds):
                    self._remote_map[item] = None
                    yield item
                    found_count += 1
                    if found_count >= max_scan:
                        self.log.info(f"Found {found_count} files in specified directory")
                        return
            else:
                self.log.warning(f"Specified source directory does not exist: {src_path}")
        
        # Try rclone lsf first for speed on FUSE mounts
        if found_count < max_scan:
            self.log.debug("Trying rclone lsf method")
            try:
                lsf = self._lsf_media(max_scan - found_count)
                if lsf:
                    self.log.info(f"Found {len(lsf)} files via rclone lsf")
                    self._remote_map.clear()
                    for mp, rel in lsf:
                        self._remote_map[mp] = rel
                        yield mp
                        found_count += 1
                        if found_count >= max_scan:
                            return
            except Exception as e:
                self.log.warning(f"rclone lsf failed: {e}")
        
        # Try fast mdfind on macOS
        if found_count < max_scan:
            self.log.debug("Trying mdfind method (macOS)")
            try:
                fast = list(self._mdfind_media(max_scan - found_count, src_dir))
                if fast:
                    self.log.info(f"Found {len(fast)} files via mdfind")
                    for mp in fast:
                        self._remote_map[mp] = None
                        yield mp
                        found_count += 1
                        if found_count >= max_scan:
                            return
            except Exception as e:
                self.log.warning(f"mdfind failed: {e}")
        
        # PRIORITY: Search Google Photos mount if it exists
        if found_count < max_scan and self.mount.exists():
            self.log.info(f"Searching Google Photos mount: {self.mount}")
            
            # First do a comprehensive recursive search of the entire mount
            try:
                mount_files = list(self._find_media_recursive(self.mount, max_scan - found_count, SETTINGS.scan_max_seconds))
                if mount_files:
                    self.log.info(f"Found {len(mount_files)} files in Google Photos mount via recursive search")
                    for item in mount_files:
                        self._remote_map[item] = None
                        yield item
                        found_count += 1
                        if found_count >= max_scan:
                            self.log.info(f"Mount search complete: found {found_count} files")
                            return
                else:
                    self.log.info("No files found in mount via recursive search, trying structured search")
            except Exception as e:
                self.log.warning(f"Recursive mount search failed: {e}, trying structured search")
            
            # If recursive didn't work or find enough, try structured search
            if found_count < max_scan:
                self.log.debug("Trying structured search of mount paths")
                media_root = self.mount / "media"
                candidates: List[Path] = []
                
                if not src_dir:  # Only use default candidates if no specific dir provided
                    try:
                        from datetime import datetime
                        y = datetime.now().year
                        recent = [str(y), str(y-1), str(y-2), str(y-3), str(y-4)]  # Search more years
                    except Exception:
                        recent = []
                    
                    # Include mount root first
                    candidates.append(self.mount)
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
                
                # Walk each candidate root with higher limits for mount
                per_root = min(max_scan - found_count, SETTINGS.scan_max_entries_per_root * 2)  # Double limit for mount
                max_sec = SETTINGS.scan_max_seconds * 2  # Double time for mount
                
                for base in candidates:
                    if found_count >= max_scan:
                        break
                    if not base.exists():
                        self.log.debug(f"Candidate path does not exist: {base}")
                        continue
                        
                    self.log.debug(f"Searching candidate path: {base}")
                    try:
                        for p in self._bfs_scandir(base, per_root, max_sec):
                            self._remote_map[p] = None
                            yield p
                            found_count += 1
                            if found_count >= max_scan:
                                break
                    except Exception as e:
                        self.log.warning(f"Error searching {base}: {e}")
                        continue
        elif found_count < max_scan:
            self.log.warning(f"Google Photos mount does not exist: {self.mount}")
            self.log.info("Set PHOTOORG_GOOGLE_MOUNT environment variable if your mount is elsewhere")
        
        # Final fallback: search common directories
        if found_count < max_scan:
            self.log.info("Using fallback search in common directories")
            try:
                for item in self._search_common_directories(max_scan - found_count):
                    self._remote_map[item] = None
                    yield item
                    found_count += 1
                    if found_count >= max_scan:
                        break
            except Exception as e:
                self.log.warning(f"Fallback search failed: {e}")
        
        self.log.info(f"Media search completed: found {found_count} files")

    def download(self, src: Path, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            subprocess.run(["/bin/cp", "-f", str(src), str(dest)], check=True)
            return
        # Try rclone copyto using the remote path mapping
        rel = self._remote_map.get(src)
        if rel:
            remote = SETTINGS.rclone_remote + rel
            subprocess.run(["rclone", "copyto", remote, str(dest)], check=True)
            return
        # Fallback attempt: cp (may fail)
        subprocess.run(["/bin/cp", "-f", str(src), str(dest)], check=True)

    def upload(self, src: Path, dest_rel: Path) -> None:
        # Place in processed_dir first; user runs rclone upload separately if desired.
        pass

