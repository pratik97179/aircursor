import cv2

from hand_tracker import HandTracker


camera = cv2.VideoCapture(0)

tracker = HandTracker()

print("Press q to quit.")

while True:

    success, frame = camera.read()

    if not success:
        break

    result = tracker.detect(frame)

    if len(result.hand_landmarks) > 0:
        frame = tracker.draw_landmarks(frame, result)

    cv2.imshow("AirCursor", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()
