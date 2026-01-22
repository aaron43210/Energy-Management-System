#!/usr/bin/env python3
"""
Quick camera test script - run this to test camera detection independently
"""

from webcam_energy import run_webcam_energy_ai
from threading import Event
import time

if __name__ == "__main__":
    print("Starting camera detection test...")
    print("Press Ctrl+C to stop\n")
    
    stop = Event()
    try:
        run_webcam_energy_ai('TestRoom', stop, camera_index=0, show_video=True)
    except KeyboardInterrupt:
        print("\n\nStopping camera...")
        stop.set()
        time.sleep(1)
        print("Camera stopped")
