from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from typing import Dict, Any
from .models import ensure_models, load_sessions
from .onnx_infer import run_photo_model
from ..config import SETTINGS


def enhance_photo_pil(im: Image.Image) -> Image.Image:
    # Lightweight enhancements that run well on Apple M-series
    # 1) Auto-contrast
    im2 = ImageOps.autocontrast(im, cutoff=1)
    # 2) Slight sharpen
    im2 = im2.filter(ImageFilter.UnsharpMask(radius=1.2, percent=130, threshold=3))
    # 3) Mild color boost
    im2 = ImageEnhance.Color(im2).enhance(1.05)
    # 4) Mild brightness/contrast tweak
    im2 = ImageEnhance.Brightness(im2).enhance(1.02)
    im2 = ImageEnhance.Contrast(im2).enhance(1.03)
    return im2


def enhance_photo(im: Image.Image) -> tuple[Image.Image, Dict[str, Any]]:
    # Try ONNX model first if available; fall back to PIL pipeline
    paths = ensure_models()
    photo_sess, _ = load_sessions(paths)
    if SETTINGS.ai_enable_enhance and photo_sess is not None:
        try:
            out = run_photo_model(photo_sess, im)
            return out, {"model": SETTINGS.photo_model_filename}
        except Exception:
            pass
    # Fallback
    return enhance_photo_pil(im), summarize_enhance()


def summarize_enhance() -> Dict[str, Any]:
    return {"enhance": {
        "autocontrast": True,
        "sharpen": "unsharp mask",
        "color_boost": 1.05,
        "brightness": 1.02,
        "contrast": 1.03,
    }}

