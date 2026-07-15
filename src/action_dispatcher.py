"""macOS cursor I/O. No interaction policy."""

import time

from AppKit import NSScreen
from Quartz.CoreGraphics import (
    CGEventCreate,
    CGEventCreateMouseEvent,
    CGEventGetLocation,
    CGEventPost,
    CGEventSetIntegerValueField,
    CGEventSourceCreate,
    CGPoint,
    CGWarpMouseCursorPosition,
    kCGEventLeftMouseDown,
    kCGEventLeftMouseUp,
    kCGEventMouseMoved,
    kCGEventSourceStateHIDSystemState,
    kCGHIDEventTap,
    kCGMouseButtonLeft,
    kCGMouseEventClickState,
    kCGSessionEventTap,
)

import config


class ActionDispatcher:

    def __init__(self):
        screen = NSScreen.mainScreen().frame()
        self._screen_width = float(screen.size.width)
        self._screen_height = float(screen.size.height)
        self._source = CGEventSourceCreate(kCGEventSourceStateHIDSystemState)

        # Track last warped position so the hot loop avoids CGEventCreate.
        x, y = self._read_os_cursor()
        self._x = x
        self._y = y
        self._last_move_event_t = 0.0
        hz = config.MOUSE_MOVE_EVENT_HZ
        self._move_event_interval = (1.0 / hz) if hz > 0 else 0.0

    def screen_size(self):
        return self._screen_width, self._screen_height

    def cursor_position(self):
        return self._x, self._y

    def set_cursor(self, x, y):
        x = max(0.0, min(x, self._screen_width - 1.0))
        y = max(0.0, min(y, self._screen_height - 1.0))
        CGWarpMouseCursorPosition(CGPoint(x, y))
        self._x = x
        self._y = y

        # Throttle move events — posting both taps every frame is very costly.
        now = time.monotonic()
        if (
            self._move_event_interval == 0.0
            or now - self._last_move_event_t >= self._move_event_interval
        ):
            self._post_mouse(kCGEventMouseMoved, x, y, dual_tap=False)
            self._last_move_event_t = now

    def click(self):
        x, y = self._x, self._y
        # Dual-tap move + click for stubborn targets (Zoom, Electron).
        self._post_mouse(kCGEventMouseMoved, x, y, dual_tap=True)
        time.sleep(0.01)
        self._post_mouse(
            kCGEventLeftMouseDown, x, y, click_state=1, dual_tap=True
        )
        time.sleep(0.02)
        self._post_mouse(
            kCGEventLeftMouseUp, x, y, click_state=1, dual_tap=True
        )

    def sync_from_os(self):
        """Refresh cached position (e.g. after external mouse move while idle)."""
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
