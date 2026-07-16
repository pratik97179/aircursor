"""AirCursor application entrypoint."""

import time

import cv2

import config
from action_dispatcher import ActionDispatcher
from camera import Camera
from gesture_engine import Gesture, GestureEngine
from hand_tracker import HandTracker
from interaction_engine import (
    Click,
    InteractionEngine,
    MouseDown,
    MouseUp,
    RightClick,
    Scroll,
    SetCursor,
    SwitchSpace,
)
from landmark_filter import LandmarkFilter
from pose_classifier import Pose, PoseClassifier
from scroll_intent_engine import ScrollIntentEngine, ScrollIntentSignal


def main():
    camera = Camera()
    tracker = HandTracker()
    landmark_filter = LandmarkFilter()
    pose_classifier = PoseClassifier()
    gesture_engine = GestureEngine()
    scroll_intent = ScrollIntentEngine()
    dispatcher = ActionDispatcher()
    screen_width, screen_height = dispatcher.screen_size()
    engine = InteractionEngine(screen_width, screen_height)

    SHOW_ACTIVE_GESTURE_LANDMARKS = True

    print("AirCursor v0.12.0")
    print(
        "Right hand = pointer; peace toggles Cursor Mode; index tip moves cursor; "
        "three-finger hold+pull scrolls."
    )
    print(
        "Left hand = thumb+index click/drag; thumb+middle right-click; "
        "open-hand swipe for Spaces."
    )
    print("Press 'q' to quit. Grant Accessibility if input fails.")

    start = time.monotonic()

    def draw_hand_landmark(frame, hand, idx, bgr, radius=6):
        if hand is None:
            return
        h, w = frame.shape[:2]
        lm = hand[idx]
        x = int(lm.x * w)
        y = int(lm.y * h)
        cv2.circle(frame, (x, y), radius, bgr, -1)

    def draw_click_hand_landmarks(frame, hand, click_signal):
        if hand is None:
            return

        if click_signal.pinched:
            draw_hand_landmark(frame, hand, 4, (0, 0, 255))
            draw_hand_landmark(frame, hand, 8, (0, 255, 0))
            draw_hand_landmark(frame, hand, 6, (0, 180, 0))
        if click_signal.right_pinched:
            draw_hand_landmark(frame, hand, 4, (0, 0, 255))
            draw_hand_landmark(frame, hand, 12, (255, 0, 0))
            draw_hand_landmark(frame, hand, 10, (180, 0, 0))
        if click_signal.open_palm:
            for tip_i, pip_i in [(8, 6), (12, 10), (16, 14), (20, 18)]:
                draw_hand_landmark(frame, hand, tip_i, (200, 200, 0), radius=6)
                draw_hand_landmark(frame, hand, pip_i, (120, 120, 0), radius=4)
            draw_hand_landmark(frame, hand, 4, (0, 0, 255))

    def draw_pointer_scroll_landmarks(frame, hand, scroll_signal):
        if hand is None:
            return
        if not (
            scroll_signal.dwelling
            or scroll_signal.armed
            or scroll_signal.scrolling
        ):
            return
        for tip_i, pip_i in [(8, 6), (12, 10), (16, 14)]:
            draw_hand_landmark(frame, hand, tip_i, (0, 180, 255), radius=7)
            draw_hand_landmark(frame, hand, pip_i, (0, 120, 200), radius=4)

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
        click_signal = gesture_engine.observe(click_hand)

        if engine.pointing:
            scroll_signal = scroll_intent.observe(pointer_hand, now)
            cursor_pos = dispatcher.cursor_position()
        else:
            scroll_intent.reset()
            scroll_signal = ScrollIntentSignal(False, False, False, 0.0, 0.0)
            cursor_pos = dispatcher.sync_from_os()

        status, commands = engine.update(
            filtered,
            pose,
            click_signal,
            scroll_signal,
            pointer_hand,
            cursor_pos,
            now,
        )

        for command in commands:
            if isinstance(command, SetCursor):
                dispatcher.set_cursor(command.x, command.y)
            elif isinstance(command, Click):
                dispatcher.click()
            elif isinstance(command, RightClick):
                dispatcher.right_click()
            elif isinstance(command, MouseDown):
                dispatcher.mouse_down()
            elif isinstance(command, MouseUp):
                dispatcher.mouse_up()
            elif isinstance(command, Scroll):
                dispatcher.scroll(command.dx, command.dy)
            elif isinstance(command, SwitchSpace):
                dispatcher.switch_space(command.direction)

        if status.pointing and status.right_clicked:
            label = "R-CLICK"
            color = (180, 80, 255)
        elif status.pointing and status.switching_space:
            label = "SPACE"
            color = (200, 100, 255)
        elif status.pointing and status.space_ready:
            label = "PALM — swipe"
            color = (200, 100, 255)
        elif status.pointing and status.dragging:
            label = "DRAG"
            color = (0, 200, 255)
        elif status.pointing and status.scrolling:
            label = "SCROLL — pull"
            color = (255, 180, 0)
        elif status.pointing and status.scroll_armed:
            label = "SCROLL — pull"
            color = (255, 180, 0)
        elif status.pointing and status.scroll_dwelling:
            label = "SCROLL — hold"
            color = (255, 140, 0)
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

        if SHOW_ACTIVE_GESTURE_LANDMARKS:
            if click_hand is not None:
                draw_click_hand_landmarks(frame, click_hand, click_signal)
            if pointer_hand is not None:
                draw_pointer_scroll_landmarks(frame, pointer_hand, scroll_signal)
                if pose == Pose.SYSTEM:
                    for tip_i, pip_i in [(8, 6), (12, 10), (16, 14), (20, 18)]:
                        draw_hand_landmark(frame, pointer_hand, tip_i, (0, 255, 255))
                        draw_hand_landmark(
                            frame, pointer_hand, pip_i, (100, 220, 220), radius=4
                        )

        cv2.imshow("AirCursor", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
