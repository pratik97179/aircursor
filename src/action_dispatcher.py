"""macOS cursor I/O. No interaction policy."""

from AppKit import NSScreen
from Quartz.CoreGraphics import (
    CGEventCreate,
    CGEventCreateKeyboardEvent,
    CGEventCreateMouseEvent,
    CGEventCreateScrollWheelEvent,
    CGEventGetLocation,
    CGEventPost,
    CGEventSetFlags,
    CGEventSetIntegerValueField,
    CGEventSourceCreate,
    CGPoint,
    CGWarpMouseCursorPosition,
    kCGEventFlagMaskControl,
    kCGEventFlagMaskSecondaryFn,
    kCGEventLeftMouseDown,
    kCGEventLeftMouseDragged,
    kCGEventLeftMouseUp,
    kCGEventMouseMoved,
    kCGEventRightMouseDown,
    kCGEventRightMouseUp,
    kCGEventSourceStateHIDSystemState,
    kCGHIDEventTap,
    kCGMouseButtonLeft,
    kCGMouseButtonRight,
    kCGMouseEventClickState,
    kCGScrollEventUnitPixel,
    kCGSessionEventTap,
)

# HID virtual keycodes
_KEYCODE_CONTROL = 59
_KEYCODE_LEFT_ARROW = 123
_KEYCODE_RIGHT_ARROW = 124

import config


class ActionDispatcher:

    def __init__(self):
        screen = NSScreen.mainScreen().frame()
        self._screen_width = float(screen.size.width)
        self._screen_height = float(screen.size.height)
        self._source = CGEventSourceCreate(kCGEventSourceStateHIDSystemState)

        x, y = self._read_os_cursor()
        self._x = x
        self._y = y
        self._button_down = False
        self._last_move_event_t = 0.0
        hz = config.MOUSE_MOVE_EVENT_HZ
        self._move_event_interval = (1.0 / hz) if hz > 0 else 0.0

    def screen_size(self):
        return self._screen_width, self._screen_height

    def cursor_position(self):
        return self._x, self._y

    def set_cursor(self, x, y):
        import time

        x = max(0.0, min(x, self._screen_width - 1.0))
        y = max(0.0, min(y, self._screen_height - 1.0))
        CGWarpMouseCursorPosition(CGPoint(x, y))
        self._x = x
        self._y = y

        now = time.monotonic()
        if (
            self._move_event_interval == 0.0
            or now - self._last_move_event_t >= self._move_event_interval
        ):
            event_type = (
                kCGEventLeftMouseDragged
                if self._button_down
                else kCGEventMouseMoved
            )
            # Dragged events need dual tap more often for Finder/apps.
            self._post_mouse(
                event_type,
                x,
                y,
                dual_tap=self._button_down,
            )
            self._last_move_event_t = now

    def click(self):
        """Atomic left click for short pinches (never leaves the button held)."""
        import time

        x, y = self._x, self._y
        self._post_mouse(kCGEventMouseMoved, x, y, dual_tap=True)
        self._post_mouse(
            kCGEventLeftMouseDown, x, y, click_state=1, dual_tap=True
        )
        time.sleep(0.02)
        self._post_mouse(
            kCGEventLeftMouseUp, x, y, click_state=1, dual_tap=True
        )
        self._button_down = False

    def right_click(self):
        """Atomic right click for thumb + middle pinches."""
        import time

        x, y = self._x, self._y
        self._post_mouse(kCGEventMouseMoved, x, y, dual_tap=True)
        self._post_mouse(
            kCGEventRightMouseDown,
            x,
            y,
            click_state=1,
            dual_tap=True,
            button=kCGMouseButtonRight,
        )
        time.sleep(0.02)
        self._post_mouse(
            kCGEventRightMouseUp,
            x,
            y,
            click_state=1,
            dual_tap=True,
            button=kCGMouseButtonRight,
        )

    def mouse_down(self):
        x, y = self._x, self._y
        self._post_mouse(kCGEventMouseMoved, x, y, dual_tap=True)
        self._post_mouse(
            kCGEventLeftMouseDown, x, y, click_state=1, dual_tap=True
        )
        self._button_down = True

    def mouse_up(self):
        x, y = self._x, self._y
        self._post_mouse(
            kCGEventLeftMouseUp, x, y, click_state=1, dual_tap=True
        )
        self._button_down = False

    def scroll(self, dx, dy):
        wheel_y = int(round(dy))
        wheel_x = int(round(dx))
        if wheel_y == 0 and wheel_x == 0:
            return

        event = CGEventCreateScrollWheelEvent(
            self._source,
            kCGScrollEventUnitPixel,
            2,
            wheel_y,
            wheel_x,
        )
        CGEventPost(kCGHIDEventTap, event)
        CGEventPost(kCGSessionEventTap, event)

    def switch_space(self, direction):
        """Switch macOS Space: -1 = Ctrl+Left, +1 = Ctrl+Right.

        Pure Quartz HID events with realistic key timing — closer to a physical
        Ctrl+Arrow tap than AppleScript (which adds latency and jank).
        """
        import time

        keycode = (
            _KEYCODE_LEFT_ARROW if direction < 0 else _KEYCODE_RIGHT_ARROW
        )
        arrow_flags = kCGEventFlagMaskControl | kCGEventFlagMaskSecondaryFn
        hold = config.SPACE_KEY_HOLD

        control_down = CGEventCreateKeyboardEvent(
            self._source, _KEYCODE_CONTROL, True
        )
        CGEventSetFlags(control_down, kCGEventFlagMaskControl)
        CGEventPost(kCGHIDEventTap, control_down)

        time.sleep(0.01)

        key_down = CGEventCreateKeyboardEvent(self._source, keycode, True)
        CGEventSetFlags(key_down, arrow_flags)
        CGEventPost(kCGHIDEventTap, key_down)

        time.sleep(hold)

        key_up = CGEventCreateKeyboardEvent(self._source, keycode, False)
        CGEventSetFlags(key_up, arrow_flags)
        CGEventPost(kCGHIDEventTap, key_up)

        time.sleep(0.01)

        control_up = CGEventCreateKeyboardEvent(
            self._source, _KEYCODE_CONTROL, False
        )
        CGEventPost(kCGHIDEventTap, control_up)

    def sync_from_os(self):
        self._x, self._y = self._read_os_cursor()
        return self._x, self._y

    def _read_os_cursor(self):
        event = CGEventCreate(None)
        location = CGEventGetLocation(event)
        return float(location.x), float(location.y)

    def _post_mouse(
        self,
        event_type,
        x,
        y,
        click_state=None,
        dual_tap=False,
        button=kCGMouseButtonLeft,
    ):
        event = CGEventCreateMouseEvent(
            self._source,
            event_type,
            (x, y),
            button,
        )
        if click_state is not None:
            CGEventSetIntegerValueField(
                event,
                kCGMouseEventClickState,
                click_state,
            )
        CGEventPost(kCGHIDEventTap, event)
        if dual_tap:
            CGEventPost(kCGSessionEventTap, event)
