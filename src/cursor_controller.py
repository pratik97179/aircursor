import pyautogui


class CursorController:

    def __init__(self):

        pyautogui.FAILSAFE = False

        self.screen_width, self.screen_height = pyautogui.size()

        self.previous_x = self.screen_width / 2
        self.previous_y = self.screen_height / 2

        self.smoothing = 0.25

        # Active region (normalized coordinates)
        self.min_x = 0.20
        self.max_x = 0.80

        self.min_y = 0.20
        self.max_y = 0.80

    def move(self, x, y):

        # Ignore movement outside the active region.
        x = min(max(x, self.min_x), self.max_x)
        y = min(max(y, self.min_y), self.max_y)

        # Remap active region to the full screen.
        x = (x - self.min_x) / (self.max_x - self.min_x)
        y = (y - self.min_y) / (self.max_y - self.min_y)

        target_x = x * self.screen_width
        target_y = y * self.screen_height

        current_x = self.previous_x + (
            target_x - self.previous_x
        ) * self.smoothing

        current_y = self.previous_y + (
            target_y - self.previous_y
        ) * self.smoothing

        pyautogui.moveTo(current_x, current_y)

        self.previous_x = current_x
        self.previous_y = current_y
