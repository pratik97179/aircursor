"""macOS cursor I/O. No interaction policy."""

from AppKit import NSScreen
from Quartz.CoreGraphics import (
    CGEventCreate,
    CGEventGetLocation,
    CGPoint,
    CGWarpMouseCursorPosition,
)


class ActionDispatcher:

    def __init__(self):
        screen = NSScreen.mainScreen().frame()
        self._screen_width = float(screen.size.width)
        self._screen_height = float(screen.size.height)

    def screen_size(self):
        return self._screen_width, self._screen_height

    def cursor_position(self):
        event = CGEventCreate(None)
        location = CGEventGetLocation(event)
        return float(location.x), float(location.y)

    def set_cursor(self, x, y):
        x = max(0.0, min(x, self._screen_width - 1.0))
        y = max(0.0, min(y, self._screen_height - 1.0))
        CGWarpMouseCursorPosition(CGPoint(x, y))
