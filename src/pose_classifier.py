"""Stateless pose family classification from a single hand's landmarks."""

from enum import Enum


class Pose(Enum):
    NONE = "none"
    POINT = "point"
    SYSTEM = "system"


class PoseClassifier:
    """
    Pointer-hand taxonomy:
    - NONE: no pointer hand
    - SYSTEM: peace (index + middle up, ring + pinky down) — mode toggle
    - POINT: pointer hand present, otherwise

    Click is not a pointer pose; the other hand pinches via GestureEngine.
    """

    def classify(self, hand):
        if hand is None:
            return Pose.NONE

        index_up = hand[8].y < hand[6].y
        middle_up = hand[12].y < hand[10].y
        ring_down = hand[16].y > hand[14].y
        pinky_down = hand[20].y > hand[18].y

        if index_up and middle_up and ring_down and pinky_down:
            return Pose.SYSTEM

        return Pose.POINT
