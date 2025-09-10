from pathlib import Path
from typing import Optional
from PIL import Image
import subprocess
import cv2
import numpy as np
from ..config import SETTINGS
from ..ai.enhance import enhance_photo_pil, summarize_enhance
from ..ai.classify import quality_scores_bgr
from ..ai.faces import detect_faces_bboxes_bgr

class PhotoProcessor:
    def enhance(self, src: Path, dest: Path, thumb_out: Path | None = None) -> dict:
        dest.parent.mkdir(parents=True, exist_ok=True)
        summary = {}
        with Image.open(src) as im:
            im = im.convert("RGB")
            if SETTINGS.ai_enable_enhance:
                im2 = enhance_photo_pil(im)
                summary.update(summarize_enhance())
            else:
                im2 = im
            im2.save(dest, quality=92, optimize=True)

        # Open with OpenCV for analysis
        bgr = cv2.imread(str(dest))
        if bgr is not None:
            if SETTINGS.ai_enable_classify:
                summary["quality"] = quality_scores_bgr(bgr)
            if SETTINGS.ai_enable_faces:
                faces = detect_faces_bboxes_bgr(bgr)
                summary["faces"] = {"count": len(faces), "bboxes": faces[:10]}

        # Thumbnail
        if thumb_out is not None:
            thumb_out.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(dest) as imf:
                imf.thumbnail((320, 320))
                imf.save(thumb_out, quality=85, optimize=True)

        # Write AI summary sidecar
        try:
            import json
            sidecar = dest.with_suffix(dest.suffix + ".ai.json")
            with sidecar.open("w") as f:
                json.dump(summary, f, indent=2)
        except Exception:
            pass

        return summary

class VideoProcessor:
    def enhance(self, src: Path, dest: Path, thumb_out: Path | None = None) -> dict:
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Simple re-encode placeholder using ffmpeg if available
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k",
            str(dest),
        ]
        subprocess.run(cmd, check=True)
        # Create a small thumbnail from middle frame if OpenCV available
        summary = {}
        try:
            cap = cv2.VideoCapture(str(dest))
            if cap and cap.isOpened():
                frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
                mid = max(frames // 2, 0)
                cap.set(cv2.CAP_PROP_POS_FRAMES, mid)
                ok, frame = cap.read()
                if ok and thumb_out is not None:
                    thumb_out.parent.mkdir(parents=True, exist_ok=True)
                    h, w = frame.shape[:2]
                    scale = 320 / max(h, w)
                    frame_small = cv2.resize(frame, (int(w*scale), int(h*scale)))
                    cv2.imwrite(str(thumb_out), frame_small)
            if cap:
                cap.release()
        except Exception:
            pass
        return summary

