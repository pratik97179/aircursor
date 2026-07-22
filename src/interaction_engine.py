"""Owns interaction state. Emits cursor commands; never talks to Quartz."""

from dataclasses import dataclass
from math import hypot

import config
from gesture_engine import Gesture
from hand_landmarks import finger_extended, is_three_finger_scroll_pose
from pose_classifier import Pose


@dataclass(frozen=True)
class SetCursor:
    x: float
    y: float


@dataclass(frozen=True)
class Click:
    """Atomic left click (down + up). Used for short pinches."""
    pass


@dataclass(frozen=True)
class RightClick:
    """Atomic right click (down + up). Thumb + middle pinch."""
    pass


@dataclass(frozen=True)
class MouseDown:
    pass


@dataclass(frozen=True)
class MouseUp:
    pass


@dataclass(frozen=True)
class Scroll:
    dx: float
    dy: float


@dataclass(frozen=True)
class SwitchSpace:
    """direction: -1 = previous (Ctrl+Left), +1 = next (Ctrl+Right)."""
    direction: int


@dataclass(frozen=True)
class EngineStatus:
    pointing: bool
    pose: Pose
    pinched: bool
    scrolling: bool
    scroll_dwelling: bool
    scroll_armed: bool
    dragging: bool
    switching_space: bool
    space_dwelling: bool
    space_ready: bool
    space_dwell_progress: float
    space_anchor: tuple[float, float] | None
    space_palm: tuple[float, float] | None
    right_clicked: bool


class InteractionEngine:

    def __init__(self, screen_width, screen_height):
        self._screen_width = float(screen_width)
        self._screen_height = float(screen_height)

        self.pointing = False

        self._system_hold_start = None
        self._system_latched = False
        self._last_press_t = None

        self._pinch_pending = False
        self._pinch_start_t = None
        self._pinch_start_tip = None
        self._primary_down = False
        self._right_pending = False
        self._right_flash = False

        self._prev_tip = None
        self._prev_t = None
        self._tracking_active = False
        self._was_scroll_active = False

        self._space_origin = None
        self._space_armed = False
        self._space_last_seen_t = None
        self._space_dwell_start = None
        self._last_space_t = None
        self._space_flash = False
        self._space_ready = False
        self._space_dwelling = False

    def update(
        self,
        filtered_hand,
        pose,
        click_signal,
        scroll_signal,
        pointer_hand,
        cursor_pos,
        t,
    ):
        commands = []
        self._space_flash = False
        self._right_flash = False

        self._handle_system_pose(pose, pointer_hand, filtered_hand, t, commands)
        # Palm arbitration before click completion so cancels win over PINCH_UP.
        self._handle_pinch_cancels(click_signal, t, commands)
        self._handle_space_swipe(click_signal, t, commands)
        self._handle_pinch(filtered_hand, click_signal, t, commands)
        self._handle_right_pinch(click_signal, t, commands)

        scroll_active = (
            self.pointing
            and (
                scroll_signal.dwelling
                or scroll_signal.armed
                or scroll_signal.scrolling
            )
        )

        if scroll_active and scroll_signal.scrolling:
            if scroll_signal.delta_y != 0.0 or scroll_signal.delta_x != 0.0:
                commands.append(
                    Scroll(dx=scroll_signal.delta_x, dy=scroll_signal.delta_y)
                )

        if scroll_active and not self._was_scroll_active:
            self._tracking_active = False

        if (
            not scroll_active
            and self._was_scroll_active
            and filtered_hand.tip is not None
        ):
            self._prev_tip = filtered_hand.tip
            self._prev_t = t
            self._tracking_active = True

        self._was_scroll_active = scroll_active

        space_active = self._space_ready or self._space_dwelling
        can_move = (
            self.pointing
            and not scroll_active
            and not space_active
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
        elif not scroll_active:
            self._tracking_active = False
            self._prev_tip = None
            self._prev_t = None

        space_dwell_progress = 0.0
        if self._space_dwelling and self._space_dwell_start is not None:
            space_dwell_progress = min(
                1.0,
                (t - self._space_dwell_start)
                / max(config.SPACE_PALM_DWELL, 1e-6),
            )

        status = EngineStatus(
            pointing=self.pointing,
            pose=pose,
            pinched=click_signal.pinched,
            scrolling=bool(self.pointing and scroll_signal.scrolling),
            scroll_dwelling=bool(self.pointing and scroll_signal.dwelling),
            scroll_armed=bool(
                self.pointing and scroll_signal.armed and not scroll_signal.scrolling
            ),
            dragging=bool(self.pointing and self._primary_down),
            switching_space=self._space_flash,
            space_dwelling=bool(self.pointing and self._space_dwelling),
            space_ready=self._space_ready,
            space_dwell_progress=space_dwell_progress,
            space_anchor=self._space_origin,
            space_palm=click_signal.palm_point,
            right_clicked=self._right_flash,
        )
        return status, commands

    def _clear_space_state(self):
        self._space_origin = None
        self._space_armed = False
        self._space_ready = False
        self._space_dwelling = False
        self._space_last_seen_t = None
        self._space_dwell_start = None

    def _handle_pinch_cancels(self, click_signal, t, commands):
        """Palm family wins: abort pending clicks; release drag without a click."""
        if click_signal.gesture == Gesture.PINCH_CANCEL:
            if self._primary_down:
                commands.append(MouseUp())
                self._primary_down = False
            self._pinch_pending = False
            self._pinch_start_t = None
            self._pinch_start_tip = None
            self._last_press_t = t
            return

        if click_signal.gesture == Gesture.RIGHT_PINCH_CANCEL:
            self._right_pending = False
            self._last_press_t = t

    def _handle_space_swipe(self, click_signal, t, commands):
        idle_for_space = (
            self.pointing
            and not self._primary_down
            and not self._pinch_pending
            and not self._right_pending
        )
        if not idle_for_space:
            self._clear_space_state()
            return

        palm = click_signal.palm_point
        open_now = click_signal.open_palm and palm is not None
        # Once armed, palm_candidate keeps tracking through mid-swipe thumb flicker
        # (common when swiping left with the left hand).
        track_now = palm is not None and (
            open_now or (self._space_ready and click_signal.palm_candidate)
        )

        if open_now:
            self._space_last_seen_t = t
            if self._space_dwell_start is None:
                self._space_dwell_start = t
                self._space_dwelling = True
                self._space_ready = False
                self._space_armed = False
                self._space_origin = None

            held = t - self._space_dwell_start
            if held < config.SPACE_PALM_DWELL:
                self._space_dwelling = True
                self._space_ready = False
                return

            # Dwell complete — arm and freeze swipe origin (ignore dwell motion).
            if not self._space_ready:
                self._space_origin = palm
                self._space_armed = True
                self._space_ready = True
            elif not self._space_armed:
                # Re-arm after a prior switch so the opposite direction can fire.
                self._space_armed = True
                if self._space_origin is None:
                    self._space_origin = palm
            self._space_dwelling = False
        elif track_now:
            self._space_last_seen_t = t
        elif (
            self._space_ready
            and self._space_last_seen_t is not None
            and t - self._space_last_seen_t <= config.SPACE_PALM_GRACE
            and palm is not None
        ):
            # Brief landmark dropout while armed — keep tracking palm point.
            pass
        else:
            self._clear_space_state()
            return

        if not self._space_armed or self._space_origin is None or palm is None:
            return

        dx = palm[0] - self._space_origin[0]
        dy = palm[1] - self._space_origin[1]
        if abs(dx) < config.SPACE_SWIPE_THRESHOLD:
            return
        if abs(dx) < config.SPACE_SWIPE_AXIS_RATIO * abs(dy):
            return

        if self._last_space_t is not None:
            if t - self._last_space_t < config.SPACE_SWIPE_COOLDOWN:
                return

        direction = -1 if dx < 0 else 1
        if config.SPACE_SWIPE_INVERT:
            direction = -direction

        commands.append(SwitchSpace(direction=direction))
        self._last_space_t = t
        self._space_flash = True
        # Re-arm at the fire point so left and right can alternate without
        # closing the palm.
        self._space_origin = palm
        self._space_armed = True
        self._space_ready = True
        self._space_dwelling = False

    def _handle_pinch(self, filtered_hand, click_signal, t, commands):
        tip = filtered_hand.tip

        if click_signal.gesture in (Gesture.PINCH_CANCEL, Gesture.RIGHT_PINCH_CANCEL):
            return

        if self.pointing and click_signal.gesture == Gesture.PINCH_DOWN:
            if (
                not self._pinch_pending
                and not self._primary_down
                and not self._right_pending
                and not self._space_ready
                and not self._space_dwelling
                and self._press_allowed(t)
            ):
                self._pinch_pending = True
                self._pinch_start_t = t
                self._pinch_start_tip = tip

        if self._pinch_pending and click_signal.pinched:
            moved = self._pinch_tip_travel(tip)
            held = t - (self._pinch_start_t or t)
            if moved >= config.DRAG_SLOP or held >= config.DRAG_ARM_HOLD:
                commands.append(MouseDown())
                self._primary_down = True
                self._pinch_pending = False
                self._last_press_t = t

        if click_signal.gesture == Gesture.PINCH_UP:
            if self._pinch_pending:
                commands.append(Click())
                self._pinch_pending = False
                self._pinch_start_t = None
                self._pinch_start_tip = None
                self._last_press_t = t
            elif self._primary_down:
                commands.append(MouseUp())
                self._primary_down = False

    def _handle_right_pinch(self, click_signal, t, commands):
        if click_signal.gesture in (Gesture.PINCH_CANCEL, Gesture.RIGHT_PINCH_CANCEL):
            return

        if self.pointing and click_signal.gesture == Gesture.RIGHT_PINCH_DOWN:
            if (
                not self._right_pending
                and not self._pinch_pending
                and not self._primary_down
                and not self._space_ready
                and not self._space_dwelling
                and self._press_allowed(t)
            ):
                self._right_pending = True

        if click_signal.gesture == Gesture.RIGHT_PINCH_UP:
            if self._right_pending:
                commands.append(RightClick())
                self._right_pending = False
                self._right_flash = True
                self._last_press_t = t

    def _pinch_tip_travel(self, tip):
        if tip is None or self._pinch_start_tip is None:
            return 0.0
        return hypot(
            tip[0] - self._pinch_start_tip[0],
            tip[1] - self._pinch_start_tip[1],
        )

    def _press_allowed(self, t):
        if self._last_press_t is None:
            return True
        return t - self._last_press_t >= config.CLICK_DEBOUNCE

    def _gain_for_speed(self, speed):
        ref = config.CURSOR_GAIN_SPEED_REF
        if ref <= 0.0:
            return config.CURSOR_GAIN_MIN

        normalized = min(1.0, speed / ref)
        blend = normalized * normalized * (3.0 - 2.0 * normalized)
        return config.CURSOR_GAIN_MIN + (
            config.CURSOR_GAIN_MAX - config.CURSOR_GAIN_MIN
        ) * blend

    def _handle_system_pose(self, pose, pointer_hand, filtered_hand, t, commands):
        if pointer_hand is not None and is_three_finger_scroll_pose(pointer_hand):
            self._system_hold_start = None
            self._system_latched = False
            return

        if pose != Pose.SYSTEM:
            self._system_hold_start = None
            self._system_latched = False
            return

        # Ring extended before latch means scroll intent, not peace toggle.
        if pointer_hand is not None and finger_extended(
            pointer_hand, 16, 14, 13
        ):
            self._system_hold_start = None
            self._system_latched = False
            return

        if self._system_hold_start is None:
            self._system_hold_start = t

        held = t - self._system_hold_start >= config.ACTIVATION_DELAY

        if held and not self._system_latched:
            self._system_latched = True
            self._toggle_pointing(filtered_hand, commands)

    def _toggle_pointing(self, filtered_hand, commands):
        if self.pointing:
            if self._primary_down:
                commands.append(MouseUp())
                self._primary_down = False
            self._pinch_pending = False
            self._pinch_start_t = None
            self._pinch_start_tip = None
            self._right_pending = False
            self._clear_space_state()
            self._was_scroll_active = False
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
        self._was_scroll_active = False
