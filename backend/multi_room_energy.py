# Multi-Room Process Orchestration
# This file manages the lifecycle of AI monitoring processes for multiple rooms.
# Provides two functions:
#   - start_ai_process(): Spawns a new thread to monitor a room
#                        Uses either RTSP stream or webcam based on configuration
#   - stop_ai_process(): Gracefully stops the monitoring thread
# Each room can run independently with its own detection thread.
# Acts as the control layer between the API server and AI workers.

import cv2
import requests
import time
import sys
from pathlib import Path
from threading import Thread, Event
from typing import Dict, Any

sys.path.append(str(Path(__file__).resolve().parent.parent))

try:
    from .person_detect import count_people
except Exception:
    from backend.person_detect import count_people

API_URL = "http://127.0.0.1:8002/api/occupancy"

def run_rtsp_energy_ai(room_id: str, rtsp_url: str, stop_event: Event):
    print(f"Connecting to RTSP stream for '{room_id}': {rtsp_url}")
    cap = cv2.VideoCapture(rtsp_url)
    
    if not cap.isOpened():
        print(f"Error: Could not open RTSP stream for room '{room_id}'.")
        return

    print(f"Connected to RTSP stream for '{room_id}'.")
    
    try:
        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                print(f"Lost connection to RTSP stream for '{room_id}'. Retrying...")
                cap.release()
                time.sleep(5)
                cap = cv2.VideoCapture(rtsp_url)
                continue

            people_count = count_people(frame)
            occupied = people_count > 0

            try:
                requests.post(API_URL, json={"room_id": room_id, "occupied": occupied}, timeout=1.0)
            except requests.exceptions.RequestException:
                print(f"Could not reach API for '{room_id}'.")
            
            time.sleep(0.5)
    finally:
        print(f"Stopping AI for '{room_id}'")
        cap.release()

def run_webcam_energy_ai(room_id: str, stop_event: Event, camera_index: int = 0):
    try:
        from .webcam_energy import run_webcam_energy_ai as run_single_webcam
    except Exception:
        from backend.webcam_energy import run_webcam_energy_ai as run_single_webcam
    run_single_webcam(room_id, stop_event, camera_index, show_video=False)

def start_ai_process(rooms_state: Dict[str, Any], room_id: str, camera_index: int = 0):
    if room_id not in rooms_state:
        print(f"Error: Unknown room '{room_id}'.")
        return

    room = rooms_state[room_id]
    if room.get("process") and room["process"].is_alive():
        print(f"AI already running for '{room_id}'.")
        return

    stop_event = Event()
    room["stop_event"] = stop_event

    if room.get("rtsp_url"):
        target_func = run_rtsp_energy_ai
        args = (room_id, room["rtsp_url"], stop_event)
    else:
        target_func = run_webcam_energy_ai
        args = (room_id, stop_event, camera_index)

    thread = Thread(target=target_func, args=args, daemon=True)
    room["process"] = thread
    thread.start()
    print(f"Started AI for '{room_id}'.")

def stop_ai_process(rooms_state: Dict[str, Any], room_id: str):
    if room_id not in rooms_state:
        print(f"Error: Unknown room '{room_id}'.")
        return

    room = rooms_state[room_id]
    if room.get("process") and room["process"].is_alive():
        print(f"Stopping AI for '{room_id}'...")
        room["stop_event"].set()
        room["process"].join(timeout=5)
        if room["process"].is_alive():
            print(f"Warning: AI thread for '{room_id}' did not stop.")
        else:
            print(f"AI stopped for '{room_id}'.")
        room["process"] = None
        room["stop_event"] = None
    else:
        print(f"No AI running for '{room_id}'.")

if __name__ == "__main__":
    """
    Test block for starting and stopping AI processes.
    """
    print("Running multi_room_energy.py in standalone test mode...")
    
    # Mock the global state for testing
    try:
        from .room_config import get_initial_rooms_state
    except Exception:
        from backend.room_config import get_initial_rooms_state
    mock_rooms_state = get_initial_rooms_state()
    
    # Test with a webcam (assuming camera 0 is available)
    test_room_webcam = "Classroom"
    print(f"\n--- Testing Webcam for '{test_room_webcam}' ---")
    start_ai_process(mock_rooms_state, test_room_webcam, camera_index=0)
    time.sleep(5) # Let it run for 5 seconds
    stop_ai_process(mock_rooms_state, test_room_webcam)
    
    # Test with a dummy RTSP URL
    test_room_rtsp = "Lab"
    mock_rooms_state[test_room_rtsp]["rtsp_url"] = "dummy_url" # This will fail to open but tests the logic
    print(f"\n--- Testing RTSP for '{test_room_rtsp}' ---")
    start_ai_process(mock_rooms_state, test_room_rtsp)
    time.sleep(2)
    stop_ai_process(mock_rooms_state, test_room_rtsp)

    print("\nStandalone test finished.")
