# =============================================================================
# Multi-Room Process Orchestration Module
# =============================================================================
# This file manages the lifecycle of AI monitoring processes for multiple rooms.
#
# Provides two main functions:
#   - start_ai_process(): Spawns a new thread to monitor a room
#   - stop_ai_process(): Gracefully stops the monitoring thread
#
# Detection modes:
#   - RTSP mode: Uses professional CCTV cameras via RTSP protocol
#   - Webcam mode: Uses local webcam for demo/testing
#
# Each room can run independently with its own detection thread.
# Acts as the control layer between the API server and AI workers.
# =============================================================================

import cv2
import requests
import time
import sys
from pathlib import Path
from threading import Thread, Event

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Import person detection module
try:
    from .person_detect import count_people
except Exception:
    from backend.person_detect import count_people

# API endpoint for sending occupancy updates
API_URL = "http://127.0.0.1:8002/api/occupancy"


def run_rtsp_energy_ai(room_id, rtsp_url, stop_event):
    """
    Runs AI detection on an RTSP camera stream.
    
    This function runs in a loop until stop_event is set:
        1. Captures frames from RTSP stream
        2. Runs person detection on each frame
        3. Sends occupancy status to API
    
    Parameters:
        room_id: Name/ID of the room being monitored
        rtsp_url: Full RTSP URL of the camera
        stop_event: Threading Event to signal when to stop
    """
    print(f"Connecting to RTSP stream for '{room_id}': {rtsp_url}")
    
    # Open video capture from RTSP URL
    cap = cv2.VideoCapture(rtsp_url)
    
    # Check if connection was successful
    if not cap.isOpened():
        print(f"Error: Could not open RTSP stream for room '{room_id}'.")
        return

    print(f"Connected to RTSP stream for '{room_id}'.")
    
    try:
        # Main detection loop - runs until stop_event is set
        while not stop_event.is_set():
            # Read a frame from the camera
            ret, frame = cap.read()
            
            # Handle connection loss
            if not ret:
                print(f"Lost connection to RTSP stream for '{room_id}'. Retrying...")
                cap.release()
                time.sleep(5)  # Wait before reconnecting
                cap = cv2.VideoCapture(rtsp_url)
                continue

            # Count people in the frame using YOLO
            people_count = count_people(frame)
            
            # Determine if room is occupied (at least 1 person)
            occupied = people_count > 0

            # Send occupancy update to API
            try:
                requests.post(
                    API_URL, 
                    json={"room_id": room_id, "occupied": occupied}, 
                    timeout=1.0
                )
            except requests.exceptions.RequestException:
                print(f"Could not reach API for '{room_id}'.")
            
            # Small delay between frames
            time.sleep(0.5)
            
    finally:
        # Clean up when stopping
        print(f"Stopping AI for '{room_id}'")
        cap.release()


def run_webcam_energy_ai(room_id, stop_event, camera_index=0):
    """
    Runs AI detection on a local webcam.
    
    This is a wrapper that calls the webcam_energy module.
    Used for demo and testing without CCTV hardware.
    
    Parameters:
        room_id: Name/ID of the room being monitored
        stop_event: Threading Event to signal when to stop
        camera_index: Index of the webcam to use (default 0)
    """
    # Import the webcam energy module
    try:
        from .webcam_energy import run_webcam_energy_ai as run_single_webcam
    except Exception:
        from backend.webcam_energy import run_webcam_energy_ai as run_single_webcam
    
    # Run webcam detection (show_video=False for background operation)
    run_single_webcam(room_id, stop_event, camera_index, show_video=False)


def start_ai_process(rooms_state, room_id, camera_index=0):
    """
    Starts an AI monitoring process for a room.
    
    Creates a new thread that runs either RTSP or webcam detection
    based on whether an RTSP URL is configured for the room.
    
    Parameters:
        rooms_state: Dictionary containing all room states
        room_id: ID of the room to start monitoring
        camera_index: Webcam index to use if not using RTSP
    """
    # Check if room exists
    if room_id not in rooms_state:
        print(f"Error: Unknown room '{room_id}'.")
        return

    room = rooms_state[room_id]
    
    # Check if AI is already running for this room
    process = room.get("process")
    if process and process.is_alive():
        print(f"AI already running for '{room_id}'.")
        return

    # Create a stop event for this room's thread
    stop_event = Event()
    room["stop_event"] = stop_event

    # Choose detection mode based on whether RTSP URL is configured
    rtsp_url = room.get("rtsp_url")
    
    if rtsp_url:
        # Use RTSP camera detection
        target_func = run_rtsp_energy_ai
        args = (room_id, rtsp_url, stop_event)
    else:
        # Use webcam detection
        target_func = run_webcam_energy_ai
        args = (room_id, stop_event, camera_index)

    # Create and start the detection thread
    thread = Thread(target=target_func, args=args, daemon=True)
    room["process"] = thread
    thread.start()
    
    print(f"Started AI for '{room_id}'.")


def stop_ai_process(rooms_state, room_id):
    """
    Stops the AI monitoring process for a room.
    
    Signals the thread to stop via stop_event and waits for it to finish.
    
    Parameters:
        rooms_state: Dictionary containing all room states
        room_id: ID of the room to stop monitoring
    """
    # Check if room exists
    if room_id not in rooms_state:
        print(f"Error: Unknown room '{room_id}'.")
        return

    room = rooms_state[room_id]
    
    # Get the process and check if it's running
    process = room.get("process")
    
    if process and process.is_alive():
        print(f"Stopping AI for '{room_id}'...")
        
        # Signal the thread to stop
        room["stop_event"].set()
        
        # Wait for thread to finish (with timeout)
        process.join(timeout=5)
        
        # Check if thread stopped successfully
        if process.is_alive():
            print(f"Warning: AI thread for '{room_id}' did not stop.")
        else:
            print(f"AI stopped for '{room_id}'.")
        
        # Clear the process references
        room["process"] = None
        room["stop_event"] = None
    else:
        print(f"No AI running for '{room_id}'.")


# =============================================================================
# Test Block - Runs when file is executed directly
# =============================================================================
if __name__ == "__main__":
    """
    Test block for starting and stopping AI processes.
    Run this file directly to test the multi-room functionality.
    """
    print("Running multi_room_energy.py in standalone test mode...")
    
    # Import room configuration
    try:
        from .room_config import get_initial_rooms_state
    except Exception:
        from backend.room_config import get_initial_rooms_state
    
    # Create mock room state for testing
    mock_rooms_state = get_initial_rooms_state()
    
    # Test 1: Webcam detection for Classroom
    test_room_webcam = "Classroom"
    print(f"\n--- Testing Webcam for '{test_room_webcam}' ---")
    start_ai_process(mock_rooms_state, test_room_webcam, camera_index=0)
    time.sleep(5)  # Let it run for 5 seconds
    stop_ai_process(mock_rooms_state, test_room_webcam)
    
    # Test 2: RTSP detection for Lab (with dummy URL - will fail but tests logic)
    test_room_rtsp = "Lab"
    mock_rooms_state[test_room_rtsp]["rtsp_url"] = "dummy_url"
    print(f"\n--- Testing RTSP for '{test_room_rtsp}' ---")
    start_ai_process(mock_rooms_state, test_room_rtsp)
    time.sleep(2)
    stop_ai_process(mock_rooms_state, test_room_rtsp)

    print("\nStandalone test finished.")
