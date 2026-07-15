"""Stateless pose family classification from hand landmarks."""

from enum import Enum


class Pose(Enum):
    NONE = "none"
    POINT = "point"
    SYSTEM = "system"


class PoseClassifier:
    """
    Release taxonomy:
    - NONE: no hand
    - SYSTEM: peace (index + middle up, ring + pinky down)
    - POINT: hand present, not SYSTEM
    """

    def classify(self, landmarks):
        if not landmarks:
            return Pose.NONE

        hand = landmarks[0]

        index_up = hand[8].y < hand[6].y
        middle_up = hand[12].y < hand[10].y
        ring_down = hand[16].y > hand[14].y
        pinky_down = hand[20].y > hand[18].y

        if index_up and middle_up and ring_down and pinky_down:
            return Pose.SYSTEM

        return Pose.POINT
