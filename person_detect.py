# ---------------------------------
# PERSON DETECTION USING AI
# ---------------------------------

from ultralytics import YOLO
import cv2

def main():
    model = YOLO("yolov8n.pt")
    camera = cv2.VideoCapture(0)

    if camera.isOpened() == False:
        print("Camera not accessible")
        return

    while True:
        ret, frame = camera.read()
        if ret == False:
            break

        results = model(frame, conf=0.4, verbose=False)
        people_count = 0

        for r in results:
            for box in r.boxes:
                if int(box.cls[0]) == 0:
                    people_count = people_count + 1
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)

        cv2.putText(frame,
                    "People Count: " + str(people_count),
                    (20,40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0,0,255),
                    2)

        cv2.imshow("Person Detection", frame)

        if cv2.waitKey(1) == 27:
            break

    camera.release()
    cv2.destroyAllWindows()

main()