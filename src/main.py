import cv2

from hand_tracker import HandTracker
from cursor_controller import CursorController

camera = cv2.VideoCapture(0)

tracker = HandTracker()
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

        index_tip = tracker.get_index_tip(result)

        frame_height, frame_width, _ = frame.shape

        camera_x = int(index_tip.x * frame_width)
        camera_y = int(index_tip.y * frame_height)

        cursor.move(
            index_tip.x,
            index_tip.y,
        )

        # Draw active region
        cv2.rectangle(
            frame,
            (
                int(cursor.min_x * frame_width),
                int(cursor.min_y * frame_height),
            ),
            (
                int(cursor.max_x * frame_width),
                int(cursor.max_y * frame_height),
            ),
            (255, 255, 0),
            2,
        )

        cv2.circle(
            frame,
            (camera_x, camera_y),
            10,
            (0, 0, 255),
            -1,
        )

    cv2.imshow("AirCursor", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()
