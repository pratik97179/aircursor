"""Stateless pose family classification from a single hand's landmarks."""

from enum import Enum

from hand_landmarks import is_peace_pose, is_three_finger_scroll_pose


class Pose(Enum):
    NONE = "none"
    POINT = "point"
    SYSTEM = "system"


class PoseClassifier:
    """
    Pointer-hand taxonomy:
    - NONE: no pointer hand
    - SYSTEM: peace (index + middle up, ring + pinky down) — mode toggle
    - POINT: pointer hand present otherwise

    Three-finger scroll pose (ring up) is never SYSTEM — handled by ScrollIntentEngine.
    """

    def classify(self, hand):
        if hand is None:
            return Pose.NONE

        if is_three_finger_scroll_pose(hand):
            return Pose.POINT

        if is_peace_pose(hand):
            return Pose.SYSTEM

        return Pose.POINT
