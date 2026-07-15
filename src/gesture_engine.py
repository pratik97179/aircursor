"""Click-hand pinch edge detection. No interaction timers."""

from enum import Enum
from math import hypot

import config


class Gesture(Enum):
    NONE = "none"
    PINCH_DOWN = "pinch_down"
    PINCH_UP = "pinch_up"


def _hand_scale(hand):
    wrist = hand[0]
    middle_mcp = hand[9]
    scale = hypot(wrist.x - middle_mcp.x, wrist.y - middle_mcp.y)
    return scale if scale > 1e-6 else 1e-6


def pinch_ratio(hand):
    """Thumb tip (4) to index tip (8), divided by hand scale."""
    thumb = hand[4]
    index = hand[8]
    distance = hypot(thumb.x - index.x, thumb.y - index.y)
    return distance / _hand_scale(hand)


class GestureEngine:
    """
    Frame-to-frame pinch edges on the click hand only.
    Owns only previous pinched bit (not click debounce / mode).
    """

    def __init__(self):
        self._pinched = False

    def reset(self):
        self._pinched = False

    def detect(self, hand):
        if hand is None:
            if self._pinched:
                self._pinched = False
                return Gesture.PINCH_UP
            return Gesture.NONE

        ratio = pinch_ratio(hand)

        if not self._pinched and ratio <= config.PINCH_ENTER:
            self._pinched = True
            return Gesture.PINCH_DOWN

        if self._pinched and ratio >= config.PINCH_EXIT:
            self._pinched = False
            return Gesture.PINCH_UP

        return Gesture.NONE

    @property
    def is_pinched(self):
        return self._pinched
