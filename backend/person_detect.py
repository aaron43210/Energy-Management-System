# YOLO Person Detection Module
# This file handles AI-based person detection using YOLOv8 neural network.
# Key features:
#   - Lazy loads the YOLO model (loaded only once, reused for all detections)
#   - count_people() function detects people in video frames
#   - Returns count of detected persons with configurable confidence threshold
# Used by both webcam and CCTV processing to determine room occupancy.

import numpy as np
from ultralytics import YOLO
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "yolov8n.pt"

_model = None

def get_model():
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"YOLO model not found at {MODEL_PATH}")
        _model = YOLO(MODEL_PATH)
    return _model

def count_people(frame: np.ndarray, conf: float = 0.4) -> int:
    if frame is None:
        return 0

    model = get_model()
    results = model(frame, conf=conf, classes=[0], verbose=False)

    if results and results[0]:
        return len(results[0].boxes)
    return 0
