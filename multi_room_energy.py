# ------------------------------------------------
# MULTI ROOM ENERGY MANAGEMENT SYSTEM
# CCTV / Camera Based Occupancy Detection
# ------------------------------------------------

from ultralytics import YOLO
import cv2
import time
from room_config import ROOMS

# ------------------------------------------------
# CONSTANTS
# ------------------------------------------------

EMPTY_TIMEOUT = 300    # 5 minutes

# ------------------------------------------------
# INITIALIZATION FUNCTION
# ------------------------------------------------

def initialize_system():
    model = YOLO("yolov8n.pt")

    cameras = {}
    for room, data in ROOMS.items():
        cameras[room] = cv2.VideoCapture(data["rtsp"])

    return model, cameras

# ------------------------------------------------
# PERSON COUNT FUNCTION
# ------------------------------------------------

def get_people_count(model, frame):
    results = model(frame, conf=0.4, verbose=False)
    count = 0

    for r in results:
        for box in r.boxes:
            if int(box.cls[0]) == 0:   # person class
                count = count + 1

    return count

# ------------------------------------------------
# ENERGY DECISION FUNCTION
# ------------------------------------------------

def energy_decision(room, people_count, current_time):
    if people_count > 0:
        ROOMS[room]["last_seen"] = current_time
        if ROOMS[room]["power"] != "ON":
            ROOMS[room]["power"] = "ON"
            print(room + ": POWER ON")

    else:
        if current_time - ROOMS[room]["last_seen"] > EMPTY_TIMEOUT:
            if ROOMS[room]["power"] != "OFF":
                ROOMS[room]["power"] = "OFF"
                print(room + ": POWER OFF")

# ------------------------------------------------
# DISPLAY FUNCTION
# ------------------------------------------------

def display_output(room, frame, people_count):
    text = room + " | People: " + str(people_count) + " | Power: " + ROOMS[room]["power"]
    cv2.putText(
        frame,
        text,
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2
    )
    cv2.imshow(room, frame)

# ------------------------------------------------
# MAIN FUNCTION
# ------------------------------------------------

def main():
    model, cameras = initialize_system()
    print("Multi-room energy management system started")

    while True:
        for room, camera in cameras.items():
            ret, frame = camera.read()
            if ret == False:
                print(room + ": CCTV not available")
                continue

            people_count = get_people_count(model, frame)
            current_time = time.time()

            energy_decision(room, people_count, current_time)
            display_output(room, frame, people_count)

        if cv2.waitKey(1) == 27:   # ESC key
            break

    for camera in cameras.values():
        camera.release()

    cv2.destroyAllWindows()

# ------------------------------------------------
# PROGRAM EXECUTION
# ------------------------------------------------

main()