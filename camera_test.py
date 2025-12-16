# -----------------------------
# CAMERA TEST PROGRAM
# -----------------------------

import cv2

def main():
    camera = cv2.VideoCapture(0)

    if camera.isOpened() == False:
        print("Camera not accessible")
        return

    print("Camera opened successfully")

    while True:
        ret, frame = camera.read()
        if ret == False:
            break

        cv2.imshow("Camera Test", frame)

        if cv2.waitKey(1) == 27:   # ESC key
            break

    camera.release()
    cv2.destroyAllWindows()

main()