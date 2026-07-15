"""AirCursor application entrypoint."""

import time

import cv2

from action_dispatcher import ActionDispatcher
from camera import Camera
from hand_tracker import HandTracker
from interaction_engine import InteractionEngine, SetCursor
from landmark_filter import LandmarkFilter
from pose_classifier import PoseClassifier


def main():
    camera = Camera()
    tracker = HandTracker()
    landmark_filter = LandmarkFilter()
    pose_classifier = PoseClassifier()
    dispatcher = ActionDispatcher()
    screen_width, screen_height = dispatcher.screen_size()
    engine = InteractionEngine(screen_width, screen_height)

    print("AirCursor v0.6")
    print("Hold a peace sign to toggle Cursor Mode. Press 'q' to quit.")
    print("Grant Accessibility permission if the cursor does not move.")

    start = time.monotonic()

    while True:
        frame = camera.read()
        if frame is None:
            break

        timestamp_ms = int((time.monotonic() - start) * 1000)
        result = tracker.detect(frame, timestamp_ms)

        landmarks = None
        tip = None

        if result.hand_landmarks:
            landmarks = result.hand_landmarks
            tip = tracker.get_control_point(result)
            frame = tracker.draw_landmarks(frame, result)

            tip_x, tip_y = tip
            height, width, _ = frame.shape
            cv2.circle(
                frame,
                (int(tip_x * width), int(tip_y * height)),
                10,
                (0, 0, 255),
                -1,
            )

        now = time.monotonic()
        filtered = landmark_filter.update(landmarks, tip, now)
        pose = pose_classifier.classify(
            filtered.landmarks if filtered.landmarks is not None else None
        )

        cursor_pos = dispatcher.cursor_position()
        status, commands = engine.update(
            filtered,
            pose,
            cursor_pos,
            now,
        )

        for command in commands:
            if isinstance(command, SetCursor):
                dispatcher.set_cursor(command.x, command.y)

        if status.pointing:
            label = "CURSOR MODE"
            color = (0, 255, 0)
        else:
            label = "IDLE"
            color = (0, 0, 255)

        cv2.putText(
            frame,
            label,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            color,
            2,
        )

        cv2.imshow("AirCursor", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
