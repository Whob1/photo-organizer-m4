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
        # Create a small thumbnail from middle frame and compute quality/face stats on sampled frames
        summary = {"frames_sampled": 0}
        try:
            cap = cv2.VideoCapture(str(dest))
            if cap and cap.isOpened():
                frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
                sample_idxs = []
                if frames > 0:
                    # sample up to 10 evenly spaced frames
                    steps = max(min(frames // 10, 30), 1)
                    sample_idxs = list(range(0, frames, steps))[:10]
                blur_vals, bright_vals, color_vals = [], [], []
                face_count_total = 0
                first_frame = None
                for idx in sample_idxs:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                    ok, frame = cap.read()
                    if not ok:
                        continue
                    if first_frame is None:
                        first_frame = frame
                    q = quality_scores_bgr(frame)
                    blur_vals.append(q["blur"]) 
                    bright_vals.append(q["brightness"]) 
                    color_vals.append(q["colorfulness"]) 
                    faces = detect_faces_bboxes_bgr(frame) if SETTINGS.ai_enable_faces else []
                    face_count_total += len(faces)
                if first_frame is not None and thumb_out is not None:
                    thumb_out.parent.mkdir(parents=True, exist_ok=True)
                    h, w = first_frame.shape[:2]
                    scale = 320 / max(h, w)
                    frame_small = cv2.resize(first_frame, (int(w*scale), int(h*scale)))
                    cv2.imwrite(str(thumb_out), frame_small)
                n = max(len(sample_idxs), 1)
                if blur_vals:
                    summary.update({
                        "quality": {
                            "blur_avg": float(sum(blur_vals)/len(blur_vals)),
                            "brightness_avg": float(sum(bright_vals)/len(bright_vals)) if bright_vals else None,
                            "colorfulness_avg": float(sum(color_vals)/len(color_vals)) if color_vals else None,
                        },
                        "faces": {"avg_per_frame": float(face_count_total / len(sample_idxs)) if sample_idxs else 0.0}
                    })
                summary["frames_sampled"] = len(sample_idxs)
            if cap:
                cap.release()
        except Exception:
            pass
        # Write AI summary sidecar next to video
        try:
            import json
            sidecar = dest.with_suffix(dest.suffix + ".ai.json")
            with open(sidecar, "w") as f:
                json.dump(summary, f, indent=2)
        except Exception:
            pass
        return summary

