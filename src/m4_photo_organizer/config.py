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
    rclone_remote: str = Field(default="googlephotos:")
    ai_enable_faces: bool = Field(default=True)
    ai_enable_classify: bool = Field(default=True)
    ai_enable_enhance: bool = Field(default=True)
    models_dir: Path = Field(default=Path("./models"))
    photo_model_filename: str = Field(default="restormer_real_denoising.pth")
    video_model_filename: str = Field(default="video_enhance.onnx")
    photo_model_url: str = Field(default="https://huggingface.co/deepinv/Restormer/resolve/main/gaussian_color_denoising_sigma25.pth?download=true")
    video_model_url: str = Field(default="https://huggingface.co/bukuroo/RealESRGAN-ONNX/resolve/main/real-esrgan-x4plus-128.onnx?download=true")
    # Additional Restormer weights
    restormer_weights: list[str] = Field(default_factory=lambda: [
        "https://huggingface.co/deepinv/Restormer/resolve/main/gaussian_color_denoising_sigma25.pth?download=true",
        "https://huggingface.co/deepinv/Restormer/resolve/main/gaussian_gray_denoising_sigma25.pth?download=true",
        "https://huggingface.co/deepinv/Restormer/resolve/main/real_denoising.pth?download=true",
        "https://huggingface.co/deepinv/Restormer/resolve/main/single_image_defocus_deblurring.pth?download=true",
        "https://huggingface.co/deepinv/Restormer/resolve/main/deraining.pth?download=true",
    ])
    # Feature flags
    ai_video_superres: bool = Field(default=True)
    ai_photo_restormer: bool = Field(default=True)
    restormer_default_weight: str = Field(default="real_denoising.pth")
    # Scanning performance tuning
    scan_max_seconds: int = Field(default=8)
    scan_max_entries_per_root: int = Field(default=2000)

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
            rclone_remote=os.getenv("PHOTOORG_RCLONE_REMOTE", "googlephotos:"),
            models_dir=Path(os.getenv("PHOTOORG_MODELS_DIR", "./models")),
            photo_model_filename=os.getenv("PHOTOORG_PHOTO_MODEL_NAME", "restormer_real_denoising.pth"),
            video_model_filename=os.getenv("PHOTOORG_VIDEO_MODEL_NAME", "video_enhance.onnx"),
            photo_model_url=os.getenv("PHOTOORG_PHOTO_MODEL_URL", "https://huggingface.co/deepinv/Restormer/resolve/main/gaussian_color_denoising_sigma25.pth?download=true"),
            video_model_url=os.getenv("PHOTOORG_VIDEO_MODEL_URL", "https://huggingface.co/bukuroo/RealESRGAN-ONNX/resolve/main/real-esrgan-x4plus-128.onnx?download=true"),
            restormer_weights=[
                os.getenv("PHOTOORG_RESTORMER_W0", "https://huggingface.co/deepinv/Restormer/resolve/main/gaussian_color_denoising_sigma25.pth?download=true"),
                os.getenv("PHOTOORG_RESTORMER_W1", "https://huggingface.co/deepinv/Restormer/resolve/main/gaussian_gray_denoising_sigma25.pth?download=true"),
                os.getenv("PHOTOORG_RESTORMER_W2", "https://huggingface.co/deepinv/Restormer/resolve/main/real_denoising.pth?download=true"),
                os.getenv("PHOTOORG_RESTORMER_W3", "https://huggingface.co/deepinv/Restormer/resolve/main/single_image_defocus_deblurring.pth?download=true"),
                os.getenv("PHOTOORG_RESTORMER_W4", "https://huggingface.co/deepinv/Restormer/resolve/main/deraining.pth?download=true"),
            ],
            ai_video_superres=os.getenv("PHOTOORG_AI_VIDEO_SR", "1") != "0",
            ai_photo_restormer=os.getenv("PHOTOORG_AI_RESTORMER", "1") != "0",
            restormer_default_weight=os.getenv("PHOTOORG_RESTORMER_WEIGHT", "real_denoising.pth"),
            scan_max_seconds=int(os.getenv("PHOTOORG_SCAN_SECONDS", "8")),
            scan_max_entries_per_root=int(os.getenv("PHOTOORG_SCAN_MAX_PER_ROOT", "2000")),
        )

SETTINGS = Settings.load()
