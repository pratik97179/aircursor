"""Signal-level tip smoothing (One Euro) and active-region gating."""

from dataclasses import dataclass
from math import tau

import config


@dataclass
class FilteredHand:
    tip: tuple[float, float] | None
    tip_valid: bool
    landmarks: object | None


def _smoothing_factor(cutoff, dt):
    if cutoff <= 0.0 or dt <= 0.0:
        return 1.0
    r = tau * cutoff * dt
    return r / (r + 1.0)


class _OneEuroAxis:
    def __init__(self):
        self._x = None
        self._dx = 0.0
        self._t = None

    def reset(self):
        self._x = None
        self._dx = 0.0
        self._t = None

    def filter(self, value, t):
        if self._x is None or self._t is None:
            self._x = value
            self._dx = 0.0
            self._t = t
            return value

        dt = t - self._t
        if dt <= 0.0:
            return self._x

        dx = (value - self._x) / dt
        edx = (
            self._dx
            + _smoothing_factor(config.ONE_EURO_D_CUTOFF, dt) * (dx - self._dx)
        )
        cutoff = config.ONE_EURO_MIN_CUTOFF + config.ONE_EURO_BETA * abs(edx)
        self._x = self._x + _smoothing_factor(cutoff, dt) * (value - self._x)
        self._dx = edx
        self._t = t
        return self._x


class LandmarkFilter:

    def __init__(self):
        self._fx = _OneEuroAxis()
        self._fy = _OneEuroAxis()
        self._miss_frames = 0
        self._last_tip = None

    def reset(self):
        self._fx.reset()
        self._fy.reset()
        self._miss_frames = 0
        self._last_tip = None

    def update(self, landmarks, tip, t):
        if landmarks is None or tip is None:
            self._miss_frames += 1
            if (
                self._miss_frames <= config.TIP_LOSS_GRACE_FRAMES
                and self._last_tip is not None
            ):
                return FilteredHand(
                    tip=self._last_tip,
                    tip_valid=False,
                    landmarks=None,
                )

            self.reset()
            return FilteredHand(tip=None, tip_valid=False, landmarks=None)

        self._miss_frames = 0
        tip_x, tip_y = tip
        smoothed = (
            self._fx.filter(tip_x, t),
            self._fy.filter(tip_y, t),
        )
        self._last_tip = smoothed

        tip_valid = (
            config.ACTIVE_REGION_LEFT
            <= smoothed[0]
            <= config.ACTIVE_REGION_RIGHT
            and config.ACTIVE_REGION_TOP
            <= smoothed[1]
            <= config.ACTIVE_REGION_BOTTOM
        )

        return FilteredHand(
            tip=smoothed,
            tip_valid=tip_valid,
            landmarks=landmarks,
        )
