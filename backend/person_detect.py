# =============================================================================
# YOLO Person Detection Module
# =============================================================================
# This file handles AI-based person detection using YOLOv8 neural network.
#
# Key features:
#   - Lazy loading: Model is loaded only once when first needed
#   - get_model(): Returns the YOLO model (loads if not already loaded)
#   - count_people(): Detects and counts people in a video frame
#
# The YOLO model is stored at the project root (yolov8n.pt)
# Class 0 in YOLO is "person" - we only detect this class
# =============================================================================

import numpy as np
from ultralytics import YOLO
from pathlib import Path
import sys

# Calculate the path to the YOLO model file
# BASE_DIR is the project root directory (parent of backend folder)
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "yolov8n.pt"

# Global variable to store the loaded model
# Using None initially - model is loaded on first use (lazy loading)
_model = None


def get_model():
    """
    Returns the YOLO model, loading it if necessary.
    
    This uses a lazy loading pattern:
        - First call: loads model from disk and caches it
        - Subsequent calls: returns the cached model
    
    This saves memory and startup time when detection isn't needed.
    
    Raises:
        FileNotFoundError: If the YOLO model file doesn't exist
    """
    global _model
    
    # Check if model is already loaded
    if _model is None:
        # Model not loaded yet - need to load it
        
        # First check if the model file exists
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"YOLO model not found at {MODEL_PATH}")
        
        # Load the YOLO model from file
        _model = YOLO(MODEL_PATH)
    
    return _model


def count_people(frame, conf=0.4):
    """
    Counts the number of people detected in a video frame.
    
    Parameters:
        frame: numpy array containing the image/video frame
        conf: Confidence threshold (0.0 to 1.0), default 0.4
              Only detections above this confidence are counted
    
    Returns:
        Integer count of people detected in the frame
        Returns 0 if frame is None or no people detected
    
    How it works:
        1. Gets the YOLO model
        2. Runs detection on the frame
        3. Filters for class 0 (person) only
        4. Returns the count of detection boxes
    """
    # Handle None frame
    if frame is None:
        return 0

    # Get the YOLO model (loads if not already loaded)
    model = get_model()
    
    # Run detection
    # - conf: minimum confidence threshold
    # - classes=[0]: only detect class 0 (person)
    # - verbose=False: don't print detection details
    results = model(frame, conf=conf, classes=[0], verbose=False)

    # Count the number of detection boxes
    if results and results[0]:
        # Each box represents one detected person
        return len(results[0].boxes)
    
    return 0
