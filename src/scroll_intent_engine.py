"""Pointer-hand three-finger scroll intent (dwell + rubber-band displacement)."""

from dataclasses import dataclass
from math import copysign

import config
from hand_landmarks import is_three_finger_scroll_pose, three_finger_centroid
from landmark_filter import _OneEuroAxis


@dataclass(frozen=True)
class ScrollIntentSignal:
    dwelling: bool
    armed: bool
    scrolling: bool
    delta_y: float
    delta_x: float


class ScrollIntentEngine:
    """
    Right-hand scroll intent:
    - Hold index + middle + ring up for SCROLL_INTENT_DWELL
    - Vertical pull from anchor drives incremental rubber-band scroll
    """

    def __init__(self):
        self._dwell_start = None
        self._grace_frames = 0
        self._armed = False
        self._anchor_y = None
        self._prev_strength = 0.0
        self._fy = _OneEuroAxis()

    def reset(self):
        self._dwell_start = None
        self._grace_frames = 0
        self._armed = False
        self._anchor_y = None
        self._prev_strength = 0.0
        self._fy.reset()

    def observe(self, hand, t):
        if hand is None or not is_three_finger_scroll_pose(hand):
            self.reset()
            return ScrollIntentSignal(False, False, False, 0.0, 0.0)

        cx, cy = three_finger_centroid(hand)
        cy = self._fy.filter(cy, t)

        if not self._armed:
            if self._dwell_start is None:
                self._dwell_start = t
            if t - self._dwell_start < config.SCROLL_INTENT_DWELL:
                return ScrollIntentSignal(True, False, False, 0.0, 0.0)

            self._armed = True
            self._anchor_y = cy
            self._prev_strength = 0.0

        d = cy - self._anchor_y
        if abs(d) < config.SCROLL_REANCHOR_THRESHOLD:
            self._prev_strength = 0.0
            return ScrollIntentSignal(False, True, False, 0.0, 0.0)

        exp = config.SCROLL_RUBBER_EXPONENT
        magnitude = config.SCROLL_RUBBER_GAIN * (abs(d) ** exp)
        strength = copysign(magnitude, d)
        delta = strength - self._prev_strength
        self._prev_strength = strength

        if config.SCROLL_NATURAL:
            delta = -delta

        cap = config.SCROLL_MAX_DELTA_PER_FRAME
        if abs(delta) > cap:
            delta = copysign(cap, delta)

        if abs(delta) < config.SCROLL_RUBBER_DEAD_ZONE:
            return ScrollIntentSignal(False, True, False, 0.0, 0.0)

        return ScrollIntentSignal(False, True, True, delta, 0.0)
