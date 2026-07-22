"""Shared finger geometry helpers — orientation-invariant (not screen-Y)."""

from math import hypot, sqrt


# MediaPipe finger joint indices: (mcp, pip, tip)
_FINGER_JOINTS = {
    "index": (5, 6, 8),
    "middle": (9, 10, 12),
    "ring": (13, 14, 16),
    "pinky": (17, 18, 20),
}

# Alignment: tip segment should roughly continue the MCP→PIP direction.
_ALIGN_DOT_MIN = 0.55
# Tip must project past PIP along MCP→PIP axis (normalized by MCP→PIP length).
_PAST_PIP_MIN = 0.35


def _xyz(lm):
    z = getattr(lm, "z", 0.0) or 0.0
    return float(lm.x), float(lm.y), float(z)


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(v):
    return sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def finger_extended(hand, tip_i, pip_i, mcp_i=None):
    """
    Finger extended in hand-local space (works when tilted).

    Uses MCP→PIP as the finger axis: tip must lie past PIP along that axis
    and PIP→TIP must align with MCP→PIP.
    """
    if hand is None:
        return False

    if mcp_i is None:
        # Infer MCP from tip index for the four long fingers.
        mcp_map = {8: 5, 12: 9, 16: 13, 20: 17}
        mcp_i = mcp_map.get(tip_i)
        if mcp_i is None:
            return False

    mcp = _xyz(hand[mcp_i])
    pip = _xyz(hand[pip_i])
    tip = _xyz(hand[tip_i])

    mcp_pip = _sub(pip, mcp)
    pip_tip = _sub(tip, pip)
    axis_len = _norm(mcp_pip)
    tip_len = _norm(pip_tip)
    if axis_len < 1e-6 or tip_len < 1e-6:
        return False

    # Project tip past PIP along MCP→PIP.
    past = _dot(_sub(tip, pip), mcp_pip) / (axis_len * axis_len)
    if past < _PAST_PIP_MIN:
        return False

    align = _dot(mcp_pip, pip_tip) / (axis_len * tip_len)
    return align >= _ALIGN_DOT_MIN


def finger_curled(hand, tip_i, pip_i, mcp_i=None):
    return not finger_extended(hand, tip_i, pip_i, mcp_i)


def finger_states(hand):
    """Return per-finger extended flags for overlay / debug."""
    if hand is None:
        return {
            "index": False,
            "middle": False,
            "ring": False,
            "pinky": False,
            "thumb_open": False,
        }

    states = {}
    for name, (mcp, pip, tip) in _FINGER_JOINTS.items():
        states[name] = finger_extended(hand, tip, pip, mcp)

    # Thumb open: tip clearly away from palm MCP cluster.
    wrist = _xyz(hand[0])
    index_mcp = _xyz(hand[5])
    pinky_mcp = _xyz(hand[17])
    palm = (
        (wrist[0] + index_mcp[0] + pinky_mcp[0]) / 3.0,
        (wrist[1] + index_mcp[1] + pinky_mcp[1]) / 3.0,
        (wrist[2] + index_mcp[2] + pinky_mcp[2]) / 3.0,
    )
    thumb_tip = _xyz(hand[4])
    hand_scale = hypot(wrist[0] - index_mcp[0], wrist[1] - index_mcp[1])
    hand_scale = hand_scale if hand_scale > 1e-6 else 1e-6
    thumb_dist = _norm(_sub(thumb_tip, palm)) / hand_scale
    states["thumb_open"] = thumb_dist >= 0.55
    return states


def is_peace_pose(hand):
    """Peace: index + middle extended, ring + pinky curled."""
    if hand is None:
        return False
    return (
        finger_extended(hand, 8, 6, 5)
        and finger_extended(hand, 12, 10, 9)
        and finger_curled(hand, 16, 14, 13)
        and finger_curled(hand, 20, 18, 17)
    )


def is_three_finger_scroll_pose(hand, require_pinky_curled=True):
    """Scroll intent: index + middle + ring extended."""
    if hand is None:
        return False
    ok = (
        finger_extended(hand, 8, 6, 5)
        and finger_extended(hand, 12, 10, 9)
        and finger_extended(hand, 16, 14, 13)
    )
    if require_pinky_curled:
        ok = ok and finger_curled(hand, 20, 18, 17)
    return ok


def three_finger_centroid(hand):
    """Midpoint of index, middle, and ring tips."""
    return (
        (hand[8].x + hand[12].x + hand[16].x) / 3.0,
        (hand[8].y + hand[12].y + hand[16].y) / 3.0,
    )
