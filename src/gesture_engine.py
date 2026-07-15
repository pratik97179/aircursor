"""Click-hand pinch edges and two-finger scroll tracking."""

from dataclasses import dataclass
from enum import Enum
from math import hypot

import config


class Gesture(Enum):
    NONE = "none"
    PINCH_DOWN = "pinch_down"
    PINCH_UP = "pinch_up"


@dataclass(frozen=True)
class ClickHandSignal:
    gesture: Gesture
    pinched: bool
    scrolling: bool
    scroll_point: tuple[float, float] | None


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


def is_two_finger_pose(hand):
    """Index + middle up, ring + pinky down — trackpad-style two fingers."""
    index_up = hand[8].y < hand[6].y
    middle_up = hand[12].y < hand[10].y
    ring_down = hand[16].y > hand[14].y
    pinky_down = hand[20].y > hand[18].y
    return index_up and middle_up and ring_down and pinky_down


def two_finger_point(hand):
    """Midpoint of index and middle tips (trackpad contact proxy)."""
    return (
        (hand[8].x + hand[12].x) * 0.5,
        (hand[8].y + hand[12].y) * 0.5,
    )


class GestureEngine:
    """
    Click-hand signals:
    - pinch edges for click
    - two-finger pose + motion point for scroll
    Pinch wins over scroll when active.
    """

    def __init__(self):
        self._pinched = False

    def reset(self):
        self._pinched = False

    def observe(self, hand):
        if hand is None:
            gesture = Gesture.NONE
            if self._pinched:
                self._pinched = False
                gesture = Gesture.PINCH_UP
            return ClickHandSignal(
                gesture=gesture,
                pinched=False,
                scrolling=False,
                scroll_point=None,
            )

        ratio = pinch_ratio(hand)
        gesture = Gesture.NONE

        if not self._pinched and ratio <= config.PINCH_ENTER:
            self._pinched = True
            gesture = Gesture.PINCH_DOWN
        elif self._pinched and ratio >= config.PINCH_EXIT:
            self._pinched = False
            gesture = Gesture.PINCH_UP

        scrolling = (
            not self._pinched
            and is_two_finger_pose(hand)
        )
        scroll_point = two_finger_point(hand) if scrolling else None

        return ClickHandSignal(
            gesture=gesture,
            pinched=self._pinched,
            scrolling=scrolling,
            scroll_point=scroll_point,
        )

    @property
    def is_pinched(self):
        return self._pinched
