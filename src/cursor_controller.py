from AppKit import NSScreen
from Quartz.CoreGraphics import (
    CGWarpMouseCursorPosition,
    CGEventCreate,
    CGEventGetLocation,
    CGPoint,
)


class CursorController:

    def __init__(self):

        screen = NSScreen.mainScreen().frame()

        self.screen_width = screen.size.width
        self.screen_height = screen.size.height

        self.anchor_cursor_x = 0
        self.anchor_cursor_y = 0

        self.anchor_hand_x = 0
        self.anchor_hand_y = 0

        self.enabled = False

        self.sensitivity = 2.0

    def toggle(self, hand_x, hand_y):

        if self.enabled:

            self.enabled = False
            return

        self.enabled = True

        event = CGEventCreate(None)
        location = CGEventGetLocation(event)

        self.anchor_cursor_x = location.x
        self.anchor_cursor_y = location.y

        self.anchor_hand_x = hand_x
        self.anchor_hand_y = hand_y

    def is_enabled(self):

        return self.enabled

    def move(self, hand_x, hand_y):

        if not self.enabled:
            return

        dx = (hand_x - self.anchor_hand_x) * self.screen_width
        dy = (hand_y - self.anchor_hand_y) * self.screen_height

        cursor_x = self.anchor_cursor_x + dx * self.sensitivity
        cursor_y = self.anchor_cursor_y + dy * self.sensitivity

        CGWarpMouseCursorPosition(
            CGPoint(cursor_x, cursor_y)
        )
    