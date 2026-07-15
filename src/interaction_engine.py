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
class EngineStatus:
    pointing: bool
    pose: Pose
    pinched: bool


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
        # False while tip is missing/outside region so resume can re-anchor.
        self._tracking_active = False

    def update(self, filtered_hand, pose, gesture, pinched, cursor_pos, t):
        commands = []

        self._handle_system_pose(pose, filtered_hand, t)

        if (
            self.pointing
            and gesture == Gesture.PINCH_DOWN
            and self._click_allowed(t)
        ):
            commands.append(Click())
            self._last_click_t = t

        # Pointer hand is independent of click-hand pinch; never freeze for click.
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
            pinched=pinched,
        )
        return status, commands

    def _click_allowed(self, t):
        if self._last_click_t is None:
            return True
        return t - self._last_click_t >= config.CLICK_DEBOUNCE

    def _gain_for_speed(self, speed):
        """Low speed → precise; high speed → faster travel."""
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
            return

        if filtered_hand.tip is None:
            return

        self.pointing = True
        self._prev_tip = filtered_hand.tip
        self._prev_t = None
        self._tracking_active = filtered_hand.tip_valid
