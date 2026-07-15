"""macOS cursor I/O. No interaction policy."""

from AppKit import NSScreen
from Quartz.CoreGraphics import (
    CGEventCreate,
    CGEventCreateMouseEvent,
    CGEventCreateScrollWheelEvent,
    CGEventGetLocation,
    CGEventPost,
    CGEventSetIntegerValueField,
    CGEventSourceCreate,
    CGPoint,
    CGWarpMouseCursorPosition,
    kCGEventLeftMouseDown,
    kCGEventLeftMouseDragged,
    kCGEventLeftMouseUp,
    kCGEventMouseMoved,
    kCGEventSourceStateHIDSystemState,
    kCGHIDEventTap,
    kCGMouseButtonLeft,
    kCGMouseEventClickState,
    kCGScrollEventUnitPixel,
    kCGSessionEventTap,
)

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

    def sync_from_os(self):
        self._x, self._y = self._read_os_cursor()
        return self._x, self._y

    def _read_os_cursor(self):
        event = CGEventCreate(None)
        location = CGEventGetLocation(event)
        return float(location.x), float(location.y)

    def _post_mouse(self, event_type, x, y, click_state=None, dual_tap=False):
        event = CGEventCreateMouseEvent(
            self._source,
            event_type,
            (x, y),
            kCGMouseButtonLeft,
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
