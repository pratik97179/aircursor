"""Click-hand pinch, right-click, two-finger scroll, and five-finger space swipe."""

from dataclasses import dataclass
from enum import Enum
from math import hypot

import config


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
    scrolling: bool
    scroll_point: tuple[float, float] | None
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


def is_two_finger_pose(hand):
    """Index + middle up, ring + pinky down — trackpad-style two fingers."""
    index_up = hand[8].y < hand[6].y
    middle_up = hand[12].y < hand[10].y
    ring_down = hand[16].y > hand[14].y
    pinky_down = hand[20].y > hand[18].y
    return index_up and middle_up and ring_down and pinky_down


def _finger_extended(hand, tip_i, pip_i):
    """Prefer tip above PIP; also accept tip clearly farther from wrist."""
    tip = hand[tip_i]
    pip = hand[pip_i]
    wrist = hand[0]
    if tip.y < pip.y:
        return True
    tip_d = hypot(tip.x - wrist.x, tip.y - wrist.y)
    pip_d = hypot(pip.x - wrist.x, pip.y - wrist.y)
    return tip_d > pip_d * 1.15


def is_open_palm(hand):
    """Four fingers extended and thumb not pinched — five-finger open hand."""
    fingers = (
        _finger_extended(hand, 8, 6)
        and _finger_extended(hand, 12, 10)
        and _finger_extended(hand, 16, 14)
        and _finger_extended(hand, 20, 18)
    )
    thumb_open = pinch_ratio(hand) >= config.PINCH_EXIT
    return fingers and thumb_open


def two_finger_point(hand):
    """Midpoint of index and middle tips (trackpad contact proxy)."""
    return (
        (hand[8].x + hand[12].x) * 0.5,
        (hand[8].y + hand[12].y) * 0.5,
    )


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
    - two-finger pose for scroll
    - open palm for Spaces swipe
    Priority: index pinch > middle pinch > open palm > two-finger scroll.
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
                scrolling=False,
                scroll_point=None,
                open_palm=False,
                palm_point=None,
            )

        index_ratio = pinch_ratio(hand)
        middle_ratio = middle_pinch_ratio(hand)
        gesture = Gesture.NONE

        # Index pinch owns the slot while active (left click / drag).
        if self._pinched:
            if index_ratio >= config.PINCH_EXIT:
                self._pinched = False
                gesture = Gesture.PINCH_UP
        elif self._right_pinched:
            if middle_ratio >= config.PINCH_EXIT:
                self._right_pinched = False
                gesture = Gesture.RIGHT_PINCH_UP
        elif index_ratio <= config.PINCH_ENTER and index_ratio <= middle_ratio:
            # Prefer thumb+index when both are close.
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
        scrolling = (
            not busy
            and not open_palm
            and is_two_finger_pose(hand)
        )

        return ClickHandSignal(
            gesture=gesture,
            pinched=self._pinched,
            right_pinched=self._right_pinched,
            scrolling=scrolling,
            scroll_point=two_finger_point(hand) if scrolling else None,
            open_palm=open_palm,
            # Always expose palm so Space swipe can ride brief detection dropouts.
            palm_point=palm_point(hand),
        )

    @property
    def is_pinched(self):
        return self._pinched
