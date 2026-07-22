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
    dwell_progress: float = 0.0
    anchor: tuple[float, float] | None = None
    centroid: tuple[float, float] | None = None


def _signal(
    dwelling=False,
    armed=False,
    scrolling=False,
    delta_y=0.0,
    delta_x=0.0,
    dwell_progress=0.0,
    anchor=None,
    centroid=None,
):
    return ScrollIntentSignal(
        dwelling=dwelling,
        armed=armed,
        scrolling=scrolling,
        delta_y=delta_y,
        delta_x=delta_x,
        dwell_progress=max(0.0, min(1.0, dwell_progress)),
        anchor=anchor,
        centroid=centroid,
    )


class ScrollIntentEngine:
    """
    Right-hand scroll intent:
    - Hold index + middle + ring up for SCROLL_INTENT_DWELL
    - Vertical pull from anchor drives incremental rubber-band scroll
    - Brief landmark dropouts during dwell/armed use SCROLL_INTENT_GRACE_FRAMES
    """

    def __init__(self):
        self._dwell_start = None
        self._miss_frames = 0
        self._armed = False
        self._anchor = None
        self._prev_strength = 0.0
        self._fy = _OneEuroAxis(min_cutoff=config.SCROLL_ONE_EURO_MIN_CUTOFF)
        self._last_centroid = None

    def reset(self):
        self._dwell_start = None
        self._miss_frames = 0
        self._armed = False
        self._anchor = None
        self._prev_strength = 0.0
        self._fy.reset()
        self._last_centroid = None

    def _dwell_progress(self, t):
        if self._dwell_start is None:
            return 0.0
        return (t - self._dwell_start) / max(config.SCROLL_INTENT_DWELL, 1e-6)

    def _pose_lost_signal(self, t):
        if self._armed:
            return _signal(
                armed=True,
                dwell_progress=1.0,
                anchor=self._anchor,
                centroid=self._last_centroid,
            )
        if self._dwell_start is not None:
            return _signal(
                dwelling=True,
                dwell_progress=self._dwell_progress(t),
                centroid=self._last_centroid,
            )
        return _signal()

    def observe(self, hand, t):
        pose_ok = hand is not None and is_three_finger_scroll_pose(hand)

        if not pose_ok:
            if self._dwell_start is not None or self._armed:
                self._miss_frames += 1
                if self._miss_frames <= config.SCROLL_INTENT_GRACE_FRAMES:
                    return self._pose_lost_signal(t)
            self.reset()
            return _signal()

        self._miss_frames = 0
        cx, cy = three_finger_centroid(hand)
        cy = self._fy.filter(cy, t)
        centroid = (cx, cy)
        self._last_centroid = centroid

        if not self._armed:
            if self._dwell_start is None:
                self._dwell_start = t
            progress = self._dwell_progress(t)
            if progress < 1.0:
                return _signal(
                    dwelling=True,
                    dwell_progress=progress,
                    centroid=centroid,
                )

            self._armed = True
            self._anchor = centroid
            self._prev_strength = 0.0

        anchor = self._anchor
        d = cy - anchor[1]
        if abs(d) < config.SCROLL_REANCHOR_THRESHOLD:
            self._prev_strength = 0.0
            return _signal(
                armed=True,
                dwell_progress=1.0,
                anchor=anchor,
                centroid=centroid,
            )

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
            return _signal(
                armed=True,
                dwell_progress=1.0,
                anchor=anchor,
                centroid=centroid,
            )

        return _signal(
            armed=True,
            scrolling=True,
            delta_y=delta,
            dwell_progress=1.0,
            anchor=anchor,
            centroid=centroid,
        )
