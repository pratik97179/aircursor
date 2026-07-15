"""Owns interaction state. Emits cursor commands; never talks to Quartz."""

from dataclasses import dataclass
from math import hypot

import config
from gesture_engine import Gesture
from pose_classifier import Pose


@dataclass(frozen=True)
class SetCursor:
    x: float
    y: float


@dataclass(frozen=True)
class Click:
    pass


@dataclass(frozen=True)
class Scroll:
    dx: float  # horizontal pixel units (positive = content right / natural)
    dy: float  # vertical pixel units (positive = content up when natural)


@dataclass(frozen=True)
class EngineStatus:
    pointing: bool
    pose: Pose
    pinched: bool
    scrolling: bool


class InteractionEngine:

    def __init__(self, screen_width, screen_height):
        self._screen_width = float(screen_width)
        self._screen_height = float(screen_height)

        self.pointing = False

        self._system_hold_start = None
        self._system_latched = False
        self._last_click_t = None

        self._prev_tip = None
        self._prev_t = None
        self._tracking_active = False

        self._prev_scroll_point = None

    def update(self, filtered_hand, pose, click_signal, cursor_pos, t):
        commands = []

        self._handle_system_pose(pose, filtered_hand, t)

        if (
            self.pointing
            and click_signal.gesture == Gesture.PINCH_DOWN
            and self._click_allowed(t)
        ):
            commands.append(Click())
            self._last_click_t = t
            self._prev_scroll_point = None

        if self.pointing and click_signal.scrolling and click_signal.scroll_point:
            point = click_signal.scroll_point
            if self._prev_scroll_point is not None:
                dx = point[0] - self._prev_scroll_point[0]
                dy = point[1] - self._prev_scroll_point[1]
                scroll = self._scroll_from_delta(dx, dy)
                if scroll is not None:
                    commands.append(scroll)
            self._prev_scroll_point = point
        else:
            self._prev_scroll_point = None

        can_move = (
            self.pointing
            and filtered_hand.tip is not None
            and filtered_hand.tip_valid
        )

        if can_move:
            tip = filtered_hand.tip
            if not self._tracking_active or self._prev_tip is None:
                self._prev_tip = tip
                self._prev_t = t
                self._tracking_active = True
            else:
                dx = tip[0] - self._prev_tip[0]
                dy = tip[1] - self._prev_tip[1]
                dt = max(t - (self._prev_t or t), 1e-3)
                speed = hypot(dx, dy) / dt
                gain = self._gain_for_speed(speed)

                cursor_x = cursor_pos[0] + dx * self._screen_width * gain
                cursor_y = cursor_pos[1] + dy * self._screen_height * gain
                commands.append(SetCursor(cursor_x, cursor_y))

                self._prev_tip = tip
                self._prev_t = t
        else:
            self._tracking_active = False
            self._prev_tip = None
            self._prev_t = None

        status = EngineStatus(
            pointing=self.pointing,
            pose=pose,
            pinched=click_signal.pinched,
            scrolling=bool(
                self.pointing and click_signal.scrolling
            ),
        )
        return status, commands

    def _scroll_from_delta(self, dx, dy):
        # Image y grows downward; fingers moving up ⇒ negative dy.
        sx = dx * config.SCROLL_GAIN_X
        sy = dy * config.SCROLL_GAIN
        if config.SCROLL_NATURAL:
            sx = -sx
            sy = -sy

        if (
            abs(sx) < config.SCROLL_DEAD_ZONE * config.SCROLL_GAIN_X
            and abs(sy) < config.SCROLL_DEAD_ZONE * config.SCROLL_GAIN
        ):
            return None

        return Scroll(dx=sx, dy=sy)

    def _click_allowed(self, t):
        if self._last_click_t is None:
            return True
        return t - self._last_click_t >= config.CLICK_DEBOUNCE

    def _gain_for_speed(self, speed):
        ref = config.CURSOR_GAIN_SPEED_REF
        if ref <= 0.0:
            return config.CURSOR_GAIN_MIN

        normalized = min(1.0, speed / ref)
        blend = normalized * normalized * (3.0 - 2.0 * normalized)
        return config.CURSOR_GAIN_MIN + (
            config.CURSOR_GAIN_MAX - config.CURSOR_GAIN_MIN
        ) * blend

    def _handle_system_pose(self, pose, filtered_hand, t):
        if pose != Pose.SYSTEM:
            self._system_hold_start = None
            self._system_latched = False
            return

        if self._system_hold_start is None:
            self._system_hold_start = t

        held = t - self._system_hold_start >= config.ACTIVATION_DELAY

        if held and not self._system_latched:
            self._system_latched = True
            self._toggle_pointing(filtered_hand)

    def _toggle_pointing(self, filtered_hand):
        if self.pointing:
            self.pointing = False
            self._tracking_active = False
            self._prev_tip = None
            self._prev_t = None
            self._prev_scroll_point = None
            return

        if filtered_hand.tip is None:
            return

        self.pointing = True
        self._prev_tip = filtered_hand.tip
        self._prev_t = None
        self._tracking_active = filtered_hand.tip_valid
        self._prev_scroll_point = None
