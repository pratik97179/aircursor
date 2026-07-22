"""AirCursor application entrypoint."""

import time

import cv2

import config
from action_dispatcher import ActionDispatcher
from camera import Camera
from gesture_engine import GestureEngine
from hand_tracker import HandTracker
from hud_renderer import HudRenderer
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
from pose_classifier import PoseClassifier
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
    hud = HudRenderer()

    print("AirCursor v0.16.1")
    print(
        "Right hand = pointer; peace toggles Cursor Mode; index tip moves cursor; "
        "three-finger hold+pull scrolls."
    )
    print(
        "Left hand = thumb+index click/drag; thumb+middle right-click; "
        "open-hand swipe for Spaces."
    )
    print("Keys: q quit · h HUD chrome · d landmark debug. Grant Accessibility if input fails.")

    start = time.monotonic()

    while True:
        frame = camera.read()
        if frame is None:
            break

        timestamp_ms = int((time.monotonic() - start) * 1000)
        result = tracker.detect(frame, timestamp_ms)

        pointer_hand, click_hand = tracker.resolve_hands(result)
        tip = tracker.get_control_point(pointer_hand)

        now = time.monotonic()
        filtered = landmark_filter.update(pointer_hand, tip, now)
        pose = pose_classifier.classify(filtered.hand)
        click_signal = gesture_engine.observe(click_hand, now)

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
                hud.note_action("CLICK", (34, 211, 238), now)
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
                label = "SPACE LEFT" if command.direction < 0 else "SPACE RIGHT"
                hud.note_action(label, (167, 139, 250), now)

        hand_count = 0
        if result.hand_landmarks:
            hand_count = len(result.hand_landmarks)

        frame = hud.render(
            frame,
            pointer_hand=pointer_hand,
            click_hand=click_hand,
            status=status,
            click_signal=click_signal,
            scroll_signal=scroll_signal,
            hand_count=hand_count,
            tip=filtered.tip if filtered.tip_valid else tip,
            now=now,
            detection_result=result,
            tracker=tracker,
        )

        cv2.imshow("AirCursor", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("h"):
            hud.toggle_chrome()
        if key == ord("d"):
            hud.toggle_debug()

    tracker.close()
    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
