from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import urllib.request
import hashlib
import os
import onnxruntime as ort
from ..config import SETTINGS

@dataclass
class ModelPaths:
    photo: Path
    video: Path


def _sha256_of_file(path: Path, chunk: int = 2 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def download_if_missing(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return False
    ensure_dir(dest.parent)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(url) as resp, tmp.open('wb') as out:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        tmp.replace(dest)
        return True
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                pass


def preferred_providers() -> list[str]:
    # Use CoreML EP on Apple Silicon if available, then CPU
    providers = []
    try:
        if os.uname().machine in ("arm64", "aarch64") and "Apple" in os.popen("sysctl -n machdep.cpu.brand_string").read():
            # CoreML EP may be available depending on onnxruntime build; if not, fallback to CPU
            providers.append("CoreMLExecutionProvider")
    except Exception:
        pass
    providers.append("CPUExecutionProvider")
    return providers


def load_sessions(paths: ModelPaths) -> tuple[Optional[ort.InferenceSession], Optional[ort.InferenceSession]]:
    photo_sess = None
    video_sess = None
    providers = preferred_providers()
    try:
        if paths.photo.exists() and paths.photo.suffix.lower() == ".onnx":
            photo_sess = ort.InferenceSession(str(paths.photo), providers=providers)
    except Exception:
        photo_sess = None
    try:
        if paths.video.exists():
            video_sess = ort.InferenceSession(str(paths.video), providers=providers)
    except Exception:
        video_sess = None
    return photo_sess, video_sess


def ensure_models() -> ModelPaths:
    models_dir = SETTINGS.models_dir
    ensure_dir(models_dir)
    photo_path = models_dir / SETTINGS.photo_model_filename
    video_path = models_dir / SETTINGS.video_model_filename
    # Download if missing (primary models)
    download_if_missing(SETTINGS.photo_model_url, photo_path)
    download_if_missing(SETTINGS.video_model_url, video_path)
    # Download additional Restormer weights into subdir for future use
    restormer_dir = models_dir / "restormer"
    ensure_dir(restormer_dir)
    for i, url in enumerate(SETTINGS.restormer_weights):
        fname = url.split("/")[-1].split("?")[0]
        download_if_missing(url, restormer_dir / fname)
    return ModelPaths(photo=photo_path, video=video_path)

