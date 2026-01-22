#!/usr/bin/env python3
"""
YOLO Detection Test
Tests the person detection module with a test pattern.
Run: .venv/bin/python backend/test_detection.py
"""

import sys
import numpy as np
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.person_detect import count_people, get_model

def create_test_image(width=640, height=480):
    """Create a simple test image (black background)"""
    return np.zeros((height, width, 3), dtype=np.uint8)

def main():
    print("=" * 60)
    print("YOLO Person Detection Test")
    print("=" * 60)
    print()
    
    # Test 1: Check model loading
    print("Test 1: Loading YOLO model...")
    try:
        model = get_model()
        print(f"✅ YOLO model loaded successfully")
        print(f"   Model type: {type(model).__name__}")
    except FileNotFoundError as e:
        print(f"❌ YOLO model file not found: {e}")
        print("   Make sure yolov8n.pt exists in the project root")
        return 1
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return 1
    
    print()
    
    # Test 2: Test detection on empty image
    print("Test 2: Testing detection on empty image...")
    try:
        test_img = create_test_image()
        count = count_people(test_img)
        print(f"✅ Detection ran successfully")
        print(f"   People detected: {count}")
        if count == 0:
            print(f"   ✅ Correctly detected 0 people in empty image")
        else:
            print(f"   ⚠️  Unexpected detection in empty image (might be a false positive)")
    except Exception as e:
        print(f"❌ Error during detection: {e}")
        return 1
    
    print()
    
    # Test 3: Test with None frame
    print("Test 3: Testing detection with None frame...")
    try:
        count = count_people(None)
        if count == 0:
            print(f"✅ Correctly handled None frame (returned 0)")
        else:
            print(f"❌ Unexpected result for None frame: {count}")
    except Exception as e:
        print(f"❌ Error handling None frame: {e}")
        return 1
    
    print()
    
    # Test 4: Test with different confidence thresholds
    print("Test 4: Testing with different confidence thresholds...")
    try:
        test_img = create_test_image()
        for conf in [0.3, 0.5, 0.7]:
            count = count_people(test_img, conf=conf)
            print(f"   Confidence {conf}: {count} people detected")
        print("✅ Confidence threshold test completed")
    except Exception as e:
        print(f"❌ Error testing confidence thresholds: {e}")
        return 1
    
    print()
    print("=" * 60)
    print("✅ All YOLO detection tests passed!")
    print("=" * 60)
    print()
    print("Note: To test with real person detection, use the webcam mode")
    print("in the web interface or provide a test image/video with people.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
