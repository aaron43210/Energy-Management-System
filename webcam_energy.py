# ---------------------------------------------
# AI BASED SMART ENERGY MANAGEMENT SYSTEM
# Webcam-Based Occupancy Detection
# ---------------------------------------------

from ultralytics import YOLO
import cv2
import time

# ---------------------------------------------
# GLOBAL VARIABLES
# ---------------------------------------------

EMPTY_TIMEOUT = 10          # seconds (keep small for testing)
power_state = "OFF"
last_seen_time = time.time()

# ---------------------------------------------
# SYSTEM INITIALIZATION
# ---------------------------------------------

def initialize_system():
    model = YOLO("yolov8n.pt")
    camera = cv2.VideoCapture(0)

    if camera.isOpened() == False:
        print("Error: Camera not accessible")
        exit()

    return model, camera

# ---------------------------------------------
# PERSON DETECTION MODULE
# ---------------------------------------------

def detect_people(model, frame):
    results = model(frame, conf=0.4, verbose=False)
    people_count = 0

    for r in results:
        for box in r.boxes:
            if int(box.cls[0]) == 0:      # person class
                people_count = people_count + 1
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    return people_count

# ---------------------------------------------
# ENERGY DECISION MODULE
# ---------------------------------------------

def energy_decision(people_count):
    global power_state, last_seen_time

    current_time = time.time()

    if people_count > 0:
        last_seen_time = current_time
        if power_state != "ON":
            power_state = "ON"
            print("MESSAGE: TURN ON ELECTRICITY")

    else:
        if current_time - last_seen_time > EMPTY_TIMEOUT:
            if power_state != "OFF":
                power_state = "OFF"
                print("MESSAGE: TURN OFF ELECTRICITY")

    return power_state

# ---------------------------------------------
# DISPLAY MODULE
# ---------------------------------------------

def display_output(frame, people_count, power):
    text = "People: " + str(people_count) + " | Power: " + power
    cv2.putText(
        frame,
        text,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 0, 255),
        2
    )
    cv2.imshow("Smart Energy Management System", frame)

# ---------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------

def main():
    model, camera = initialize_system()
    print("System started successfully")

    while True:
        ret, frame = camera.read()
        if ret == False:
            break

        people_count = detect_people(model, frame)
        power = energy_decision(people_count)
        display_output(frame, people_count, power)

        if cv2.waitKey(1) == 27:   # ESC key
            break

    camera.release()
    cv2.destroyAllWindows()

# ---------------------------------------------
# PROGRAM EXECUTION
# ---------------------------------------------

main()