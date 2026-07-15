import cv2

from cursor_controller import CursorController
from gesture_engine import Gesture, GestureEngine
from hand_tracker import HandTracker

camera = cv2.VideoCapture(0)

tracker = HandTracker()
gesture_engine = GestureEngine()
cursor = CursorController()

print("Press 'q' to quit.")

while True:

    success, frame = camera.read()

    if not success:
        break

    frame = cv2.flip(frame, 1)

    result = tracker.detect(frame)

    if result.hand_landmarks:

        frame = tracker.draw_landmarks(frame, result)

        hand_x, hand_y = tracker.get_control_point(result)

        frame_height, frame_width, _ = frame.shape

        camera_x = int(hand_x * frame_width)
        camera_y = int(hand_y * frame_height)

        gesture = gesture_engine.detect(
            result.hand_landmarks
        )

        if gesture == Gesture.TOGGLE_CURSOR:

            cursor.toggle(
                hand_x,
                hand_y,
            )

        cursor.move(
            hand_x,
            hand_y,
        )

        if cursor.is_enabled():

            status = "CURSOR MODE"
            color = (0, 255, 0)

        else:

            status = "IDLE"
            color = (0, 0, 255)

        cv2.circle(
            frame,
            (camera_x, camera_y),
            10,
            (0, 0, 255),
            -1,
        )

        cv2.putText(
            frame,
            status,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            color,
            2,
        )

    else:

        gesture_engine.detect(None)

    cv2.imshow("AirCursor", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()
