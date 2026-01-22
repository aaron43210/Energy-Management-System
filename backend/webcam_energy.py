# =============================================================================
# Webcam Energy AI Module
# =============================================================================
# This file handles webcam-based person detection for demo and testing.
#
# Features:
#   - Captures video from device camera
#   - Runs real-time YOLO detection
#   - Displays detection overlays (bounding boxes, person count)
#   - Sends occupancy updates to backend API
#   - Shows live feedback on camera window
#
# This module can be run:
#   - As a background process controlled by the API server
#   - Standalone for testing (run this file directly)
#
# Great for demonstrations and quick testing without CCTV hardware.
# =============================================================================

import cv2
import requests
import time
import sys
from pathlib import Path
from threading import Event

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Import person detection module
try:
    from .person_detect import count_people, get_model
except Exception:
    from backend.person_detect import count_people, get_model

# API endpoint for sending occupancy updates
API_URL = "http://127.0.0.1:8002/api/occupancy"


def run_webcam_energy_ai(room_id, stop_event, camera_index=0, show_video=True):
    """
    Runs AI-based person detection on a webcam feed.
    
    This function:
        1. Opens the webcam
        2. Runs YOLO detection on each frame
        3. Sends occupancy updates to the API
        4. Optionally displays the video with overlays
    
    Parameters:
        room_id: Name/ID of the room being monitored
        stop_event: Threading Event to signal when to stop
        camera_index: Index of the webcam to use (default 0)
        show_video: Whether to display the video window (default True)
    """
    print(f"Attempting to open camera at index {camera_index} for room '{room_id}'...")
    
    # Open the webcam
    cap = cv2.VideoCapture(camera_index)
    
    # Check if camera opened successfully
    if not cap.isOpened():
        print(f"❌ Error: Camera not accessible at index {camera_index} for room '{room_id}'.")
        print(f"   This could be due to:")
        print(f"   1. Camera is already in use by another process")
        print(f"   2. On macOS: Terminal/VS Code needs camera permissions (System Preferences > Security & Privacy > Camera)")
        print(f"   3. Camera index {camera_index} is incorrect")
        return

    # Set buffer size to reduce latency
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    print(f"✅ Camera opened successfully for '{room_id}'")
    print(f"Camera window display: {'ENABLED' if show_video else 'DISABLED'}")
    
    # Load the YOLO model
    try:
        model = get_model()
    except Exception as e:
        print(f"Error loading YOLO: {e}")
        cap.release()
        return

    try:
        # Main detection loop - runs until stop_event is set
        while not stop_event.is_set():
            # Read a frame from the camera
            ret, frame = cap.read()
            
            if not ret:
                print(f"Error: Failed to capture frame for '{room_id}'.")
                time.sleep(1)
                continue

            # Run YOLO detection
            # - conf=0.4: minimum 40% confidence
            # - classes=[0]: only detect class 0 (person)
            # - verbose=False: don't print detection details
            results = model(frame, conf=0.4, classes=[0], verbose=False)
            
            # Count detected people
            people_count = 0
            if results and results[0]:
                boxes = results[0].boxes
                people_count = len(boxes)
                
                # Draw bounding boxes for each detected person
                for box in boxes:
                    # Get box coordinates
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    confidence = box.conf[0].item()
                    
                    # Draw rectangle around person
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Draw confidence label
                    label = f"Person ({confidence:.2f})"
                    cv2.putText(
                        frame,
                        label,
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        2
                    )

            # Determine if room is occupied
            occupied = people_count > 0

            # Send occupancy update to API
            try:
                requests.post(
                    API_URL,
                    json={"room_id": room_id, "occupied": occupied},
                    timeout=0.5
                )
            except requests.exceptions.RequestException:
                # API might not be running - continue anyway
                pass

            # Draw video overlays if display is enabled
            if show_video:
                # Draw room name header
                cv2.putText(
                    frame,
                    f"Room: {room_id} | Webcam Test",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    2
                )

                # Draw people count
                color = (0, 255, 0) if occupied else (0, 0, 255)
                cv2.putText(
                    frame,
                    f"People: {people_count}",
                    (20, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.5,
                    color,
                    3
                )

                # Draw occupancy status
                occupancy_text = "OCCUPIED" if occupied else "EMPTY"
                occupancy_color = (0, 255, 0) if occupied else (0, 0, 255)
                cv2.putText(
                    frame,
                    f"Status: {occupancy_text}",
                    (20, 140),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    occupancy_color,
                    2
                )

                # Draw light state
                light_state = "ON" if occupied else "OFF"
                light_color = (0, 255, 0) if occupied else (255, 0, 0)
                cv2.putText(
                    frame,
                    f"Light: {light_state}",
                    (20, 190),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    light_color,
                    2
                )

                # Draw instruction
                cv2.putText(
                    frame,
                    "Press ESC to stop",
                    (20, frame.shape[0] - 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (200, 200, 200),
                    1
                )

                # Try to display the window
                if show_video:
                    try:
                        cv2.imshow(f"Energy AI - {room_id} (Press ESC to exit)", frame)
                        
                        # Check for ESC key press
                        if cv2.waitKey(1) & 0xFF == 27:
                            print(f"ESC pressed. Stopping AI for '{room_id}'.")
                            stop_event.set()
                    except Exception as e:
                        print(f"⚠️ Warning: Could not display window ({e})")
                        print(f"   Camera is running and processing frames in background")
                        show_video = False  # Disable display for rest of session
                else:
                    # Still need to process events even without display
                    time.sleep(0.01)
            
    finally:
        # Clean up
        print(f"Stopping AI for '{room_id}'")
        cap.release()
        if show_video:
            cv2.destroyAllWindows()


# =============================================================================
# Test Block - Runs when file is executed directly
# =============================================================================
if __name__ == "__main__":
    """
    Test block for running webcam detection standalone.
    Press ESC in the video window or Ctrl+C in terminal to stop.
    """
    # Use a test room ID
    TEST_ROOM_ID = "Demo Room"
    
    # Create a stop event that can be triggered by Ctrl+C
    main_stop_event = Event()

    # Signal handler for Ctrl+C
    def signal_handler(sig, frame):
        print("\nCtrl+C detected. Signaling stop to all threads.")
        main_stop_event.set()

    import signal
    signal.signal(signal.SIGINT, signal_handler)

    # Run the webcam detection
    try:
        run_webcam_energy_ai(
            room_id=TEST_ROOM_ID,
            stop_event=main_stop_event,
            show_video=True
        )
    except Exception as e:
        print(f"An unexpected error occurred during standalone test: {e}")

    print("Standalone test finished.")

