"""Click-hand pinch, right-click, and five-finger space swipe."""

from dataclasses import dataclass
from enum import Enum
from math import hypot

import config
from hand_landmarks import finger_extended


class Gesture(Enum):
    NONE = "none"
    PINCH_DOWN = "pinch_down"
    PINCH_UP = "pinch_up"
    RIGHT_PINCH_DOWN = "right_pinch_down"
    RIGHT_PINCH_UP = "right_pinch_up"


@dataclass(frozen=True)
class ClickHandSignal:
    gesture: Gesture
    pinched: bool
    right_pinched: bool
    open_palm: bool
    palm_point: tuple[float, float] | None


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


def middle_pinch_ratio(hand):
    """Thumb tip (4) to middle tip (12), divided by hand scale."""
    thumb = hand[4]
    middle = hand[12]
    distance = hypot(thumb.x - middle.x, thumb.y - middle.y)
    return distance / _hand_scale(hand)


def is_open_palm(hand):
    """Four fingers extended and thumb not pinched — five-finger open hand."""
    fingers = (
        finger_extended(hand, 8, 6)
        and finger_extended(hand, 12, 10)
        and finger_extended(hand, 16, 14)
        and finger_extended(hand, 20, 18)
    )
    thumb_open = pinch_ratio(hand) >= config.PINCH_EXIT
    return fingers and thumb_open


def palm_point(hand):
    """Palm proxy: average of wrist + finger MCPs."""
    pts = (hand[0], hand[5], hand[9], hand[13], hand[17])
    return (
        sum(p.x for p in pts) / 5.0,
        sum(p.y for p in pts) / 5.0,
    )


class GestureEngine:
    """
    Click-hand signals:
    - thumb+index pinch edges for left click/drag
    - thumb+middle pinch edges for right click
    - open palm for Spaces swipe
    Priority: index pinch > middle pinch > open palm.
    """

    def __init__(self):
        self._pinched = False
        self._right_pinched = False

    def reset(self):
        self._pinched = False
        self._right_pinched = False

    def observe(self, hand):
        if hand is None:
            gesture = Gesture.NONE
            if self._pinched:
                self._pinched = False
                gesture = Gesture.PINCH_UP
            elif self._right_pinched:
                self._right_pinched = False
                gesture = Gesture.RIGHT_PINCH_UP
            return ClickHandSignal(
                gesture=gesture,
                pinched=False,
                right_pinched=False,
                open_palm=False,
                palm_point=None,
            )

        index_ratio = pinch_ratio(hand)
        middle_ratio = middle_pinch_ratio(hand)
        gesture = Gesture.NONE

        if self._pinched:
            if index_ratio >= config.PINCH_EXIT:
                self._pinched = False
                gesture = Gesture.PINCH_UP
        elif self._right_pinched:
            if middle_ratio >= config.PINCH_EXIT:
                self._right_pinched = False
                gesture = Gesture.RIGHT_PINCH_UP
        elif index_ratio <= config.PINCH_ENTER and index_ratio <= middle_ratio:
            self._pinched = True
            gesture = Gesture.PINCH_DOWN
        elif (
            middle_ratio <= config.PINCH_ENTER
            and middle_ratio < index_ratio
        ):
            self._right_pinched = True
            gesture = Gesture.RIGHT_PINCH_DOWN

        busy = self._pinched or self._right_pinched
        open_palm = not busy and is_open_palm(hand)

        return ClickHandSignal(
            gesture=gesture,
            pinched=self._pinched,
            right_pinched=self._right_pinched,
            open_palm=open_palm,
            palm_point=palm_point(hand),
        )

    @property
    def is_pinched(self):
        return self._pinched
