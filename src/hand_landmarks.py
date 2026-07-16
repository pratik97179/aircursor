"""Shared finger extension and pose helpers for both hands."""

from math import hypot


def finger_extended(hand, tip_i, pip_i):
    """Tip above PIP, or clearly farther from wrist than PIP."""
    tip = hand[tip_i]
    pip = hand[pip_i]
    wrist = hand[0]
    if tip.y < pip.y:
        return True
    tip_d = hypot(tip.x - wrist.x, tip.y - wrist.y)
    pip_d = hypot(pip.x - wrist.x, pip.y - wrist.y)
    return tip_d > pip_d * 1.15


def finger_up(hand, tip_i, pip_i):
    """Strict tip-above-PIP check (used for peace / scroll poses)."""
    return hand[tip_i].y < hand[pip_i].y


def finger_down(hand, tip_i, pip_i):
    return hand[tip_i].y > hand[pip_i].y


def is_peace_pose(hand):
    """Peace: index + middle up, ring + pinky down."""
    if hand is None:
        return False
    return (
        finger_up(hand, 8, 6)
        and finger_up(hand, 12, 10)
        and finger_down(hand, 16, 14)
        and finger_down(hand, 20, 18)
    )


def is_three_finger_scroll_pose(hand, require_pinky_down=True):
    """Scroll intent: index + middle + ring up."""
    if hand is None:
        return False
    ok = (
        finger_extended(hand, 8, 6)
        and finger_extended(hand, 12, 10)
        and finger_extended(hand, 16, 14)
    )
    if require_pinky_down:
        ok = ok and finger_down(hand, 20, 18)
    return ok


def three_finger_centroid(hand):
    """Midpoint of index, middle, and ring tips."""
    return (
        (hand[8].x + hand[12].x + hand[16].x) / 3.0,
        (hand[8].y + hand[12].y + hand[16].y) / 3.0,
    )
