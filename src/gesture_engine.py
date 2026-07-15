"""Click-hand pinch, two-finger scroll, and five-finger space swipe."""

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
    - pinch edges for click/drag
    - two-finger pose for scroll
    - open palm for Spaces swipe
    Priority: pinch > open palm > two-finger scroll.
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
                open_palm=False,
                palm_point=None,
            )

        ratio = pinch_ratio(hand)
        gesture = Gesture.NONE

        if not self._pinched and ratio <= config.PINCH_ENTER:
            self._pinched = True
            gesture = Gesture.PINCH_DOWN
        elif self._pinched and ratio >= config.PINCH_EXIT:
            self._pinched = False
            gesture = Gesture.PINCH_UP

        open_palm = not self._pinched and is_open_palm(hand)
        scrolling = (
            not self._pinched
            and not open_palm
            and is_two_finger_pose(hand)
        )

        return ClickHandSignal(
            gesture=gesture,
            pinched=self._pinched,
            scrolling=scrolling,
            scroll_point=two_finger_point(hand) if scrolling else None,
            open_palm=open_palm,
            # Always expose palm so Space swipe can ride brief detection dropouts.
            palm_point=palm_point(hand),
        )

    @property
    def is_pinched(self):
        return self._pinched
