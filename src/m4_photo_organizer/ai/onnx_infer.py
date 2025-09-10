import numpy as np
from PIL import Image
from typing import Optional, Tuple
import onnxruntime as ort


def _preprocess_image_rgb(im: Image.Image) -> np.ndarray:
    # Convert to float32 NCHW [1,3,H,W], normalize to [0,1]
    arr = np.asarray(im.convert("RGB"), dtype=np.float32) / 255.0
    chw = np.transpose(arr, (2, 0, 1))
    return np.expand_dims(chw, 0)


def _postprocess_image_rgb(tensor: np.ndarray) -> Image.Image:
    # Expecting NCHW in [0,1]; clip and convert back to uint8 PIL
    chw = np.squeeze(tensor, 0)
    chw = np.clip(chw, 0.0, 1.0)
    h, w = chw.shape[1], chw.shape[2]
    hwc = np.transpose(chw, (1, 2, 0))
    arr = (hwc * 255.0).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def run_photo_model(session: ort.InferenceSession, im: Image.Image) -> Image.Image:
    # Try to infer the input/output names generically
    inputs = session.get_inputs()
    outputs = session.get_outputs()
    x = _preprocess_image_rgb(im)
    ort_inputs = {inputs[0].name: x}
    y = session.run([outputs[0].name], ort_inputs)[0]
    return _postprocess_image_rgb(y)

