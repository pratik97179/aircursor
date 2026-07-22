"""Click-hand pinch, right-click, and open-palm Spaces — mutually exclusive families."""

from dataclasses import dataclass
from enum import Enum
from math import hypot

import config
from hand_landmarks import finger_states


class Gesture(Enum):
    NONE = "none"
    PINCH_DOWN = "pinch_down"
    PINCH_UP = "pinch_up"
    PINCH_CANCEL = "pinch_cancel"
    RIGHT_PINCH_DOWN = "right_pinch_down"
    RIGHT_PINCH_UP = "right_pinch_up"
    RIGHT_PINCH_CANCEL = "right_pinch_cancel"


@dataclass(frozen=True)
class ClickHandSignal:
    gesture: Gesture
    pinched: bool
    right_pinched: bool
    open_palm: bool
    palm_candidate: bool
    palm_point: tuple[float, float] | None


def _hand_scale(hand):
    wrist = hand[0]
    middle_mcp = hand[9]
    scale = hypot(wrist.x - middle_mcp.x, wrist.y - middle_mcp.y)
    return scale if scale > 1e-6 else 1e-6


def pinch_ratio(hand):
    """Thumb tip (4) to index tip (8), divided by hand scale."""
    thumb = hand[4]
    index = hand[8]
    distance = hypot(thumb.x - index.x, thumb.y - index.y)
    return distance / _hand_scale(hand)


def middle_pinch_ratio(hand):
    """Thumb tip (4) to middle tip (12), divided by hand scale."""
    thumb = hand[4]
    middle = hand[12]
    distance = hypot(thumb.x - middle.x, thumb.y - middle.y)
    return distance / _hand_scale(hand)


def is_palm_candidate(hand):
    """Opening/closing transition: at least three long fingers extended."""
    if hand is None:
        return False
    states = finger_states(hand)
    count = sum(
        1
        for name in ("index", "middle", "ring", "pinky")
        if states[name]
    )
    return count >= 3


def is_fist(hand):
    """All four long fingers curled — thumb may rest on tips; not a click."""
    if hand is None:
        return False
    states = finger_states(hand)
    return not (
        states["index"]
        or states["middle"]
        or states["ring"]
        or states["pinky"]
    )


def is_pinch_shell(hand):
    """Shared pinch shell: ring + pinky curled (blocks palm / three-finger)."""
    if hand is None:
        return False
    states = finger_states(hand)
    return (not states["ring"]) and (not states["pinky"])


def is_open_palm(hand):
    """Four fingers extended and thumb not pinched — five-finger open hand."""
    states = finger_states(hand)
    fingers = (
        states["index"]
        and states["middle"]
        and states["ring"]
        and states["pinky"]
    )
    thumb_open = states["thumb_open"] and pinch_ratio(hand) >= config.PINCH_EXIT
    return fingers and thumb_open


def palm_point(hand):
    """Palm proxy: average of wrist + finger MCPs."""
    pts = (hand[0], hand[5], hand[9], hand[13], hand[17])
    return (
        sum(p.x for p in pts) / 5.0,
        sum(p.y for p in pts) / 5.0,
    )


class GestureEngine:
    """
    Click-hand signals with palm/pinch/fist arbitration:
    - Left click: index extended, thumb nearer index than middle (margin)
    - Right click: middle extended, thumb nearer middle than index (margin);
      index may stay slightly up — that used to cancel right-click mid-gesture
    - Fist (all curled): never starts a pinch; cancels an active one
    - Palm candidate (≥3 fingers up): cancels pinch, blocks new pinches
    - Open palm: Spaces arming (downstream dwell + swipe)
    """

    def __init__(self):
        self._pinched = False
        self._right_pinched = False
        self._lockout_until = 0.0
        self._was_palmish = False

    def reset(self):
        self._pinched = False
        self._right_pinched = False
        self._lockout_until = 0.0
        self._was_palmish = False

    def _locked(self, now):
        return now < self._lockout_until

    def _arm_lockout(self, now):
        self._lockout_until = now + config.PALM_PINCH_LOCKOUT

    def observe(self, hand, now):
        if hand is None:
            gesture = Gesture.NONE
            if self._pinched:
                self._pinched = False
                gesture = Gesture.PINCH_UP
            elif self._right_pinched:
                self._right_pinched = False
                gesture = Gesture.RIGHT_PINCH_UP
            if self._was_palmish:
                self._arm_lockout(now)
                self._was_palmish = False
            return ClickHandSignal(
                gesture=gesture,
                pinched=False,
                right_pinched=False,
                open_palm=False,
                palm_candidate=False,
                palm_point=None,
            )

        states = finger_states(hand)
        palm_cand = is_palm_candidate(hand)
        open_palm = is_open_palm(hand)
        palmish = palm_cand or open_palm
        fist = is_fist(hand)
        shell = is_pinch_shell(hand)
        locked = self._locked(now)

        if self._was_palmish and not palmish:
            self._arm_lockout(now)
            locked = True
        self._was_palmish = palmish

        index_ratio = pinch_ratio(hand)
        middle_ratio = middle_pinch_ratio(hand)
        margin = config.PINCH_TARGET_MARGIN
        gesture = Gesture.NONE

        # Cancel only on palm / fist — not on brief index flicker mid right-click.
        if self._pinched and (palm_cand or fist):
            self._pinched = False
            gesture = Gesture.PINCH_CANCEL
            if palm_cand:
                self._arm_lockout(now)
        elif self._right_pinched and (palm_cand or fist):
            self._right_pinched = False
            gesture = Gesture.RIGHT_PINCH_CANCEL
            if palm_cand:
                self._arm_lockout(now)
        elif self._pinched:
            if index_ratio >= config.PINCH_EXIT:
                self._pinched = False
                gesture = Gesture.PINCH_UP
        elif self._right_pinched:
            if middle_ratio >= config.PINCH_EXIT:
                self._right_pinched = False
                gesture = Gesture.RIGHT_PINCH_UP
        elif not locked and not palm_cand and not fist and shell:
            # Prefer the tip the thumb is clearly closer to.
            want_right = (
                states["middle"]
                and middle_ratio <= config.PINCH_ENTER
                and middle_ratio + margin < index_ratio
            )
            want_left = (
                states["index"]
                and index_ratio <= config.PINCH_ENTER
                and index_ratio + margin <= middle_ratio
            )
            if want_right and (not want_left or middle_ratio < index_ratio):
                self._right_pinched = True
                gesture = Gesture.RIGHT_PINCH_DOWN
            elif want_left:
                self._pinched = True
                gesture = Gesture.PINCH_DOWN

        busy = self._pinched or self._right_pinched
        open_palm_out = (not busy) and open_palm

        return ClickHandSignal(
            gesture=gesture,
            pinched=self._pinched,
            right_pinched=self._right_pinched,
            open_palm=open_palm_out,
            palm_candidate=palm_cand,
            palm_point=palm_point(hand),
        )

    @property
    def is_pinched(self):
        return self._pinched
