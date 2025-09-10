from typing import Dict, Any
import numpy as np
import cv2


def quality_scores_bgr(img_bgr: np.ndarray) -> Dict[str, Any]:
    # Blur score: variance of Laplacian
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # Brightness: mean intensity
    brightness = float(gray.mean())

    # Colorfulness: Hasler and Süsstrunk metric approximation
    (B, G, R) = cv2.split(img_bgr.astype("float"))
    rg = np.abs(R - G)
    yb = np.abs(0.5 * (R + G) - B)
    std_rg, mean_rg = np.std(rg), np.mean(rg)
    std_yb, mean_yb = np.std(yb), np.mean(yb)
    colorfulness = float(np.sqrt(std_rg**2 + std_yb**2) + 0.3 * np.sqrt(mean_rg**2 + mean_yb**2))

    tags = []
    if blur < 80:
        tags.append("blurry")
    if brightness < 60:
        tags.append("low_light")
    if colorfulness > 40:
        tags.append("vivid")

    return {
        "blur": blur,
        "brightness": brightness,
        "colorfulness": colorfulness,
        "tags": tags,
    }

