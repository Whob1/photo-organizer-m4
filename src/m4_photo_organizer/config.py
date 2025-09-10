from pathlib import Path
from pydantic import BaseModel, Field
import os

class Settings(BaseModel):
    google_photos_mount: Path = Field(default=Path("/Users/sheldon/GooglePhotos"))
    work_dir: Path = Field(default=Path("./data"))
    raw_dir: Path = Field(default=Path("./data/raw"))
    processed_dir: Path = Field(default=Path("./data/processed"))
    tmp_dir: Path = Field(default=Path("./data/tmp"))
    thumbnails_dir: Path = Field(default=Path("./data/thumbnails"))
    max_disk_bytes: int = Field(default=5 * 1024 * 1024 * 1024)  # 5GB
    db_path: Path = Field(default=Path("./data/state.db"))
    concurrent_tasks: int = Field(default=4)
    ai_enable_faces: bool = Field(default=True)
    ai_enable_classify: bool = Field(default=True)
    ai_enable_enhance: bool = Field(default=True)

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
            thumbnails_dir=work / "thumbnails",
            max_disk_bytes=max_bytes,
            db_path=work / "state.db",
            ai_enable_faces=os.getenv("PHOTOORG_AI_FACES", "1") != "0",
            ai_enable_classify=os.getenv("PHOTOORG_AI_CLASSIFY", "1") != "0",
            ai_enable_enhance=os.getenv("PHOTOORG_AI_ENHANCE", "1") != "0",
        )

SETTINGS = Settings.load()

