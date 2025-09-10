from pathlib import Path
from typing import List
import os
import shutil
import psutil
from .config import SETTINGS

class StorageManager:
    def __init__(self, max_bytes: int | None = None):
        self.max_bytes = max_bytes or SETTINGS.max_disk_bytes
        for d in [SETTINGS.raw_dir, SETTINGS.processed_dir, SETTINGS.tmp_dir]:
            Path(d).mkdir(parents=True, exist_ok=True)

    def usage_bytes(self) -> int:
        total = 0
        for p in [SETTINGS.raw_dir, SETTINGS.tmp_dir, SETTINGS.processed_dir]:
            for root, _, files in os.walk(p):
                for f in files:
                    fp = Path(root) / f
                    try:
                        total += fp.stat().st_size
                    except FileNotFoundError:
                        pass
        return total

    def ensure_room(self, need_bytes: int) -> bool:
        return self.usage_bytes() + need_bytes <= self.max_bytes

    def clean_tmp(self):
        shutil.rmtree(SETTINGS.tmp_dir, ignore_errors=True)
        Path(SETTINGS.tmp_dir).mkdir(parents=True, exist_ok=True)

