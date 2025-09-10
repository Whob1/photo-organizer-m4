from __future__ import annotations
from pathlib import Path
from typing import Optional, Dict, Any


def _mps_device_available() -> bool:
    try:
        import torch
        return torch.backends.mps.is_available() and torch.backends.mps.is_built()
    except Exception:
        return False


class RestormerRunner:
    def __init__(self, weight_path: Path):
        import torch
        self.torch = torch
        self.device = torch.device("mps") if _mps_device_available() else torch.device("cpu")
        # Import Restormer architecture, prefer vendored file then basicsr
        Restormer = None
        try:
            from ..vendor.restormer_arch import Restormer as VendoredRestormer  # type: ignore
            Restormer = VendoredRestormer
        except Exception:
            try:
                from basicsr.archs.restormer_arch import Restormer as BSRestormer  # type: ignore
                Restormer = BSRestormer
            except Exception as e:
                raise RuntimeError("Restormer architecture not available: install 'basicsr' or provide vendor file src/m4_photo_organizer/vendor/restormer_arch.py") from e
        # Instantiate model and load weights
        self.model = Restormer()
        state = torch.load(str(weight_path), map_location="cpu")
        # Some checkpoints wrap the state dict under a 'params' or 'state_dict' key
        if isinstance(state, dict):
            for k in ("params", "state_dict", "model", "net"):
                if k in state and isinstance(state[k], dict):
                    state = state[k]
                    break
        self.model.load_state_dict(state, strict=False)
        self.model.to(self.device)
        self.model.eval()

    @staticmethod
    def _to_tensor(im):
        import numpy as np
        arr = np.asarray(im.convert("RGB")) / 255.0
        arr = arr.astype("float32")
        arr = arr.transpose(2, 0, 1)  # CHW
        import torch
        ten = torch.from_numpy(arr).unsqueeze(0)
        return ten

    @staticmethod
    def _to_image(tensor):
        import numpy as np
        import PIL.Image as Image
        ten = tensor.detach().cpu().clamp(0.0, 1.0).squeeze(0).numpy()
        ten = ten.transpose(1, 2, 0)
        arr = (ten * 255.0).astype("uint8")
        return Image.fromarray(arr, mode="RGB")

    def enhance(self, im) -> Dict[str, Any]:
        x = self._to_tensor(im).to(self.device)
        with self.torch.inference_mode():
            y = self.model(x)
        out = self._to_image(y)
        return {"image": out, "engine": "restormer", "device": str(self.device)}
