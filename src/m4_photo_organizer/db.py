import sqlite3
from pathlib import Path
from typing import Iterable, Optional
import hashlib

SCHEMA = """
CREATE TABLE IF NOT EXISTS processed (
  id INTEGER PRIMARY KEY,
  rel_path TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  phash TEXT,
  media_type TEXT NOT NULL,
  processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(rel_path),
  UNIQUE(sha256)
);
"""

class DB:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.executescript(SCHEMA)
            # Best-effort schema evolution
            try:
                conn.execute("ALTER TABLE processed ADD COLUMN phash TEXT")
            except sqlite3.OperationalError:
                pass

    def has_hash(self, sha256: str) -> bool:
        with sqlite3.connect(self.path) as conn:
            cur = conn.execute("SELECT 1 FROM processed WHERE sha256=?", (sha256,))
            return cur.fetchone() is not None

    def has_path(self, rel_path: str) -> bool:
        with sqlite3.connect(self.path) as conn:
            cur = conn.execute("SELECT 1 FROM processed WHERE rel_path=?", (rel_path,))
            return cur.fetchone() is not None

    def add(self, rel_path: str, sha256: str, media_type: str, phash: str | None = None):
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO processed(rel_path, sha256, phash, media_type) VALUES(?,?,?,?)",
                (rel_path, sha256, phash, media_type),
            )
            conn.commit()


def sha256_file(path: Path, chunk_size: int = 2 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

