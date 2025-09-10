import numpy as np
from PIL import Image
import onnxruntime as ort

def _preprocess_bgr(img_bgr: np.ndarray) -> np.ndarray:
    # Expect [H,W,3] BGR uint8 -> [1,3,H,W] float32 0..1 RGB if model expects RGB.
    # RealESRGAN ONNX variants typically take RGB normalized 0..1.
    rgb = img_bgr[:, :, ::-1].astype(np.float32) / 255.0
    chw = np.transpose(rgb, (2, 0, 1))
    return np.expand_dims(chw, 0)


def _postprocess_bgr(out: np.ndarray) -> np.ndarray:
    # Expect [1,3,H,W] float32 0..1 -> uint8 BGR
    chw = np.squeeze(out, 0)
    chw = np.clip(chw, 0.0, 1.0)
    hwc = np.transpose(chw, (1, 2, 0))
    rgb = (hwc * 255.0).astype(np.uint8)
    bgr = rgb[:, :, ::-1]
    return bgr


def enhance_frame_realesrgan(session: ort.InferenceSession, frame_bgr: np.ndarray, tile: int | None = 0, overlap: int = 8) -> np.ndarray:
    # Tile processing to reduce memory if requested
    H, W = frame_bgr.shape[:2]
    if not tile or tile <= 0:
        x = _preprocess_bgr(frame_bgr)
        out = session.run([session.get_outputs()[0].name], {session.get_inputs()[0].name: x})[0]
        return _postprocess_bgr(out)
    else:
        scale = 4  # for RealESRGAN x4
        out_img = np.zeros((H*scale, W*scale, 3), dtype=np.uint8)
        for y in range(0, H, tile - overlap):
            for x0 in range(0, W, tile - overlap):
                y1 = min(y + tile, H)
                x1 = min(x0 + tile, W)
                crop = frame_bgr[y:y1, x0:x1]
                crop_out = enhance_frame_realesrgan(session, crop, tile=0)
                oy = y*scale
                ox = x0*scale
                out_img[oy:oy+crop_out.shape[0], ox:ox+crop_out.shape[1]] = crop_out
        return out_img

