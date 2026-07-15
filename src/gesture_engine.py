from enum import Enum
import time


class Gesture(Enum):
    NONE = "none"
    TOGGLE_CURSOR = "toggle_cursor"


class GestureEngine:

    def __init__(self):
        self.gesture_held = False
        self.activation_start_time = None

        # Hold gesture for 400 ms before toggling.
        self.activation_delay = 0.4

    def detect(self, hand_landmarks):

        if not hand_landmarks:
            self.gesture_held = False
            self.activation_start_time = None
            return Gesture.NONE

        hand = hand_landmarks[0]

        # Finger states
        index = hand[8].y < hand[6].y
        middle = hand[12].y < hand[10].y
        ring = hand[16].y > hand[14].y
        pinky = hand[20].y > hand[18].y

        peace_sign = (
            index
            and middle
            and ring
            and pinky
        )

        if peace_sign:

            # First frame of the gesture.
            if self.activation_start_time is None:
                self.activation_start_time = time.monotonic()

            # Gesture held long enough.
            elif (
                time.monotonic() - self.activation_start_time
                >= self.activation_delay
            ):

                if not self.gesture_held:
                    self.gesture_held = True
                    return Gesture.TOGGLE_CURSOR

        else:

            self.gesture_held = False
            self.activation_start_time = None

        return Gesture.NONE
