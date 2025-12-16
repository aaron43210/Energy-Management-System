# ---------------------------------------------
# ENERGY MANAGEMENT LOGIC USING AI
# Webcam Based Occupancy Detection
# ---------------------------------------------

from ultralytics import YOLO
import cv2
import time

# ---------------------------------------------
# GLOBAL VARIABLES
# ---------------------------------------------

EMPTY_TIMEOUT = 120      # 2 minutes
power_state = "OFF"
last_seen_time = time.time()

# ---------------------------------------------
# INITIALIZATION FUNCTION
# ---------------------------------------------

def initialize_system():
    model = YOLO("yolov8n.pt")
    camera = cv2.VideoCapture(0)

    if camera.isOpened() == False:
        print("Camera not accessible")
        exit()

    return model, camera

# ---------------------------------------------
# PERSON COUNT FUNCTION
# ---------------------------------------------

def get_people_count(model, frame):
    results = model(frame, conf=0.4, verbose=False)
    count = 0

    for r in results:
        for box in r.boxes:
            if int(box.cls[0]) == 0:   # person class
                count = count + 1

    return count

# ---------------------------------------------
# ENERGY DECISION FUNCTION
# ---------------------------------------------

def energy_decision(people_count):
    global power_state, last_seen_time

    current_time = time.time()

    if people_count > 0:
        last_seen_time = current_time
        if power_state != "ON":
            power_state = "ON"
            print("POWER ON")

    else:
        if current_time - last_seen_time > EMPTY_TIMEOUT:
            if power_state != "OFF":
                power_state = "OFF"
                print("POWER OFF")

    return power_state

# ---------------------------------------------
# DISPLAY FUNCTION
# ---------------------------------------------

def display_status(frame, people_count, power):
    text = "People: " + str(people_count) + " | Power: " + power
    cv2.putText(
        frame,
        text,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 0, 0),
        2
    )
    cv2.imshow("Energy Management AI", frame)

# ---------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------

def main():
    model, camera = initialize_system()

    while True:
        ret, frame = camera.read()
        if ret == False:
            break

        people_count = get_people_count(model, frame)
        power = energy_decision(people_count)
        display_status(frame, people_count, power)

        if cv2.waitKey(1) == 27:   # ESC key
            break

    camera.release()
    cv2.destroyAllWindows()

# ---------------------------------------------
# PROGRAM START
# ---------------------------------------------

main()