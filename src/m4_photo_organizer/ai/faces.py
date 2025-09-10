from typing import List, Dict, Any
import cv2
import numpy as np


def detect_faces_bboxes_bgr(img_bgr: np.ndarray) -> List[Dict[str, int]]:
    # Haar classifier included with OpenCV; lightweight and CPU-friendly
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(48, 48))
    results = []
    for (x, y, w, h) in faces:
        results.append({"x": int(x), "y": int(y), "w": int(w), "h": int(h)})
    return results

