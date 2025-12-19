# Webcam Energy AI Module
# This file handles webcam-based person detection for demo and testing.
# Features:
#   - Captures video from device camera
#   - Runs real-time YOLO detection
#   - Displays detection overlays (bounding boxes, person count)
#   - Sends occupancy updates to backend API
#   - Shows live feedback on camera window
# Runs as background process controlled by the API server.
# Great for demonstrations and quick testing without CCTV hardware.

import cv2
import requests
import time
import sys
from pathlib import Path
from threading import Event

sys.path.append(str(Path(__file__).resolve().parent.parent))

try:
    from .person_detect import count_people, get_model
except Exception:
    from backend.person_detect import count_people, get_model

API_URL = "http://127.0.0.1:8002/api/occupancy"

def run_webcam_energy_ai(
    room_id: str,
    stop_event: Event,
    camera_index: int = 0,
    show_video: bool = True
):
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"Error: Camera not accessible at index {camera_index} for room '{room_id}'.")
        return

    print(f"Starting AI for '{room_id}'")
    print(f"Camera opened. Press ESC to stop.")
    
    try:
        model = get_model()
    except Exception as e:
        print(f"Error loading YOLO: {e}")
        cap.release()
        return

    try:
        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                print(f"Error: Failed to capture frame for '{room_id}'.")
                time.sleep(1)
                continue

            results = model(frame, conf=0.4, classes=[0], verbose=False)
            
            people_count = 0
            if results and results[0]:
                boxes = results[0].boxes
                people_count = len(boxes)
                
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    confidence = box.conf[0].item()
                    
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
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

            occupied = people_count > 0

            try:
                requests.post(
                    API_URL,
                    json={"room_id": room_id, "occupied": occupied},
                    timeout=0.5
                )
            except requests.exceptions.RequestException:
                pass

            if show_video:
                cv2.putText(
                    frame,
                    f"Room: {room_id} | Webcam Test",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    2
                )

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

                cv2.putText(
                    frame,
                    "Press ESC to stop",
                    (20, frame.shape[0] - 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (200, 200, 200),
                    1
                )

                cv2.imshow(f"Energy AI - {room_id} (Press ESC to exit)", frame)

                if cv2.waitKey(1) & 0xFF == 27:
                    print(f"ESC pressed. Stopping AI for '{room_id}'.")
                    stop_event.set()
            
    finally:
        print(f"Stopping AI for '{room_id}'")
        cap.release()
        if show_video:
            cv2.destroyAllWindows()
    
    # Use a dummy room ID for testing
    TEST_ROOM_ID = "Demo Room"
    
    # Create a stop event that can be triggered by Ctrl+C
    main_stop_event = Event()

    def signal_handler(sig, frame):
        print("\nCtrl+C detected. Signaling stop to all threads.")
        main_stop_event.set()

    import signal
    signal.signal(signal.SIGINT, signal_handler)

    try:
        run_webcam_energy_ai(
            room_id=TEST_ROOM_ID,
            stop_event=main_stop_event,
            show_video=True
        )
    except Exception as e:
        print(f"An unexpected error occurred during standalone test: {e}")

    print("Standalone test finished.")

