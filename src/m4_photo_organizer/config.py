from pathlib import Path
from pydantic import BaseModel, Field
import os

class Settings(BaseModel):
    google_photos_mount: Path = Field(default=Path("/Users/sheldon/GooglePhotos"))
    work_dir: Path = Field(default=Path("./data"))
    raw_dir: Path = Field(default=Path("./data/raw"))
    processed_dir: Path = Field(default=Path("./data/processed"))
    tmp_dir: Path = Field(default=Path("./data/tmp"))
    max_disk_bytes: int = Field(default=5 * 1024 * 1024 * 1024)  # 5GB
    db_path: Path = Field(default=Path("./data/state.db"))
    concurrent_tasks: int = Field(default=4)

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def load(cls) -> "Settings":
        # env overrides
        mount = Path(os.getenv("PHOTOORG_GOOGLE_MOUNT", "/Users/sheldon/GooglePhotos"))
        max_bytes = int(os.getenv("PHOTOORG_MAX_DISK_BYTES", str(5 * 1024 * 1024 * 1024)))
        work = Path(os.getenv("PHOTOORG_WORK_DIR", "./data"))
        return cls(
            google_photos_mount=mount,
            work_dir=work,
            raw_dir=work / "raw",
            processed_dir=work / "processed",
            tmp_dir=work / "tmp",
            max_disk_bytes=max_bytes,
            db_path=work / "state.db",
        )

SETTINGS = Settings.load()

