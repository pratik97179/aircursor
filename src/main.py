"""AirCursor application entrypoint."""

import time

import cv2

from action_dispatcher import ActionDispatcher
from camera import Camera
from gesture_engine import GestureEngine
from hand_tracker import HandTracker
from interaction_engine import Click, InteractionEngine, SetCursor
from landmark_filter import LandmarkFilter
from pose_classifier import PoseClassifier
import config


def main():
    camera = Camera()
    tracker = HandTracker()
    landmark_filter = LandmarkFilter()
    pose_classifier = PoseClassifier()
    gesture_engine = GestureEngine()
    dispatcher = ActionDispatcher()
    screen_width, screen_height = dispatcher.screen_size()
    engine = InteractionEngine(screen_width, screen_height)

    print("AirCursor v0.7")
    print(
        "Right hand = pointer (peace toggles Cursor Mode; index tip moves cursor)."
    )
    print(
        "Left hand = click (pinch thumb + index to left-click)."
    )
    print("Press 'q' to quit. Grant Accessibility if cursor/click fail.")

    start = time.monotonic()

    while True:
        frame = camera.read()
        if frame is None:
            break

        timestamp_ms = int((time.monotonic() - start) * 1000)
        result = tracker.detect(frame, timestamp_ms)

        pointer_hand, click_hand = tracker.resolve_hands(result)
        tip = tracker.get_control_point(pointer_hand)

        if config.SHOW_LANDMARKS and result.hand_landmarks:
            frame = tracker.draw_landmarks(frame, result)

        if tip is not None:
            height, width = frame.shape[:2]
            tip_x, tip_y = tip
            cv2.circle(
                frame,
                (int(tip_x * width), int(tip_y * height)),
                10,
                (0, 0, 255),
                -1,
            )

        now = time.monotonic()
        filtered = landmark_filter.update(pointer_hand, tip, now)
        pose = pose_classifier.classify(filtered.hand)
        gesture = gesture_engine.detect(click_hand)

        # While not actively pointing, resync from OS (user may move mouse).
        if engine.pointing:
            cursor_pos = dispatcher.cursor_position()
        else:
            cursor_pos = dispatcher.sync_from_os()

        status, commands = engine.update(
            filtered,
            pose,
            gesture,
            gesture_engine.is_pinched,
            cursor_pos,
            now,
        )

        for command in commands:
            if isinstance(command, SetCursor):
                dispatcher.set_cursor(command.x, command.y)
            elif isinstance(command, Click):
                dispatcher.click()

        if status.pointing and status.pinched:
            label = "CLICK"
            color = (255, 200, 0)
        elif status.pointing:
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
