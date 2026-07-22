"""Regression: palm/pinch mutual exclusion and Spaces dwell + axis gate."""

from __future__ import annotations

import os
import sys
import unittest
from dataclasses import dataclass

# Allow `uv run python -m unittest` from repo root without install.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import config
from gesture_engine import Gesture, GestureEngine
from interaction_engine import (
    Click,
    InteractionEngine,
    MouseDown,
    MouseUp,
    RightClick,
    SwitchSpace,
)
from landmark_filter import FilteredHand
from pose_classifier import Pose
from scroll_intent_engine import ScrollIntentSignal


@dataclass
class LM:
    x: float
    y: float
    z: float = 0.0


def _hand():
    return [LM(0.5, 0.65) for _ in range(21)]


def _set_finger(hand, mcp, pip, tip, *, extended, x):
    hand[mcp] = LM(x, 0.55)
    if extended:
        hand[pip] = LM(x, 0.42)
        hand[tip] = LM(x, 0.28)
    else:
        hand[pip] = LM(x, 0.50)
        hand[tip] = LM(x, 0.53)


def _set_thumb(hand, tip_xy, ip_xy=None):
    hand[1] = LM(0.42, 0.58)
    hand[2] = LM(0.40, 0.55)
    hand[3] = LM(*(ip_xy or (0.38, 0.50)))
    hand[4] = LM(*tip_xy)


def make_open_palm(ox=0.0, oy=0.0):
    hand = _hand()
    hand[0] = LM(0.50 + ox, 0.70 + oy)
    for mcp, pip, tip, x in (
        (5, 6, 8, 0.46),
        (9, 10, 12, 0.50),
        (13, 14, 16, 0.54),
        (17, 18, 20, 0.58),
    ):
        hand[mcp] = LM(x + ox, 0.55 + oy)
        hand[pip] = LM(x + ox, 0.42 + oy)
        hand[tip] = LM(x + ox, 0.28 + oy)
    _set_thumb(hand, (0.32 + ox, 0.42 + oy))
    return hand


def make_fist(thumb_on_tips=False):
    """Closed fist. Optionally put thumb on curled tips (the false-click case)."""
    hand = _hand()
    hand[0] = LM(0.50, 0.70)
    for mcp, pip, tip, x in (
        (5, 6, 8, 0.46),
        (9, 10, 12, 0.50),
        (13, 14, 16, 0.54),
        (17, 18, 20, 0.58),
    ):
        _set_finger(hand, mcp, pip, tip, extended=False, x=x)
    if thumb_on_tips:
        # Thumb resting on curled index tip — looks like pinch by distance alone.
        _set_thumb(hand, (hand[8].x + 0.005, hand[8].y + 0.005))
    else:
        _set_thumb(hand, (0.48, 0.58))
    return hand


def make_index_pinch(close=True):
    """Pinch family: ring+pinky curled; thumb near/far from index tip."""
    hand = _hand()
    hand[0] = LM(0.50, 0.70)
    _set_finger(hand, 5, 6, 8, extended=True, x=0.46)
    _set_finger(hand, 9, 10, 12, extended=False, x=0.50)
    _set_finger(hand, 13, 14, 16, extended=False, x=0.54)
    _set_finger(hand, 17, 18, 20, extended=False, x=0.58)
    if close:
        _set_thumb(hand, (hand[8].x + 0.01, hand[8].y + 0.01))
    else:
        _set_thumb(hand, (0.32, 0.42))
    return hand


def make_middle_pinch(close=True, index_also_up=False):
    """Right-click pinch. index_also_up mimics real hands mid-gesture."""
    hand = _hand()
    hand[0] = LM(0.50, 0.70)
    _set_finger(hand, 5, 6, 8, extended=index_also_up, x=0.46)
    _set_finger(hand, 9, 10, 12, extended=True, x=0.50)
    _set_finger(hand, 13, 14, 16, extended=False, x=0.54)
    _set_finger(hand, 17, 18, 20, extended=False, x=0.58)
    if close:
        _set_thumb(hand, (hand[12].x + 0.01, hand[12].y + 0.01))
    else:
        _set_thumb(hand, (0.32, 0.42))
    return hand


def make_palm_candidate_three():
    """Three fingers up — palm candidate, not full open palm (pinky curled)."""
    hand = _hand()
    hand[0] = LM(0.50, 0.70)
    _set_finger(hand, 5, 6, 8, extended=True, x=0.46)
    _set_finger(hand, 9, 10, 12, extended=True, x=0.50)
    _set_finger(hand, 13, 14, 16, extended=True, x=0.54)
    _set_finger(hand, 17, 18, 20, extended=False, x=0.58)
    _set_thumb(hand, (0.45, 0.50))  # intermediate thumb near fingers
    return hand


def _idle_scroll():
    return ScrollIntentSignal(False, False, False, 0.0, 0.0)


def _filtered(tip=(0.5, 0.4)):
    return FilteredHand(tip=tip, tip_valid=True, hand=None)


class GestureEngineArbitrationTests(unittest.TestCase):
    def test_fist_with_thumb_on_tips_is_not_a_click(self):
        eng = GestureEngine()
        sig = eng.observe(make_fist(thumb_on_tips=True), 10.0)
        self.assertEqual(sig.gesture, Gesture.NONE)
        self.assertFalse(sig.pinched)
        self.assertFalse(sig.right_pinched)

    def test_pinch_cancelled_when_closing_to_fist(self):
        eng = GestureEngine()
        t = 10.0
        eng.observe(make_index_pinch(close=True), t)
        cancel = eng.observe(make_fist(thumb_on_tips=True), t + 0.05)
        self.assertEqual(cancel.gesture, Gesture.PINCH_CANCEL)
        self.assertFalse(cancel.pinched)

    def test_open_then_close_palm_no_pinch_click(self):
        eng = GestureEngine()
        t = 1.0
        # Opening path: fist → candidate → open → close → fist
        for hand in (
            make_fist(),
            make_palm_candidate_three(),
            make_open_palm(),
            make_palm_candidate_three(),
            make_fist(),
        ):
            sig = eng.observe(hand, t)
            t += 0.05
            self.assertNotEqual(sig.gesture, Gesture.PINCH_DOWN)
            self.assertNotEqual(sig.gesture, Gesture.PINCH_UP)

    def test_fist_to_open_palm_no_pinch(self):
        eng = GestureEngine()
        t = 1.0
        gestures = []
        for hand in (make_fist(), make_palm_candidate_three(), make_open_palm()):
            gestures.append(eng.observe(hand, t).gesture)
            t += 0.05
        self.assertNotIn(Gesture.PINCH_DOWN, gestures)
        self.assertNotIn(Gesture.PINCH_UP, gestures)

    def test_deliberate_index_pinch_emits_down_up(self):
        eng = GestureEngine()
        t = 10.0  # past any lockout
        down = eng.observe(make_index_pinch(close=True), t)
        self.assertEqual(down.gesture, Gesture.PINCH_DOWN)
        self.assertTrue(down.pinched)
        up = eng.observe(make_index_pinch(close=False), t + 0.1)
        self.assertEqual(up.gesture, Gesture.PINCH_UP)

    def test_deliberate_middle_pinch_emits_right(self):
        eng = GestureEngine()
        t = 10.0
        down = eng.observe(make_middle_pinch(close=True), t)
        self.assertEqual(down.gesture, Gesture.RIGHT_PINCH_DOWN)
        up = eng.observe(make_middle_pinch(close=False), t + 0.1)
        self.assertEqual(up.gesture, Gesture.RIGHT_PINCH_UP)

    def test_right_click_survives_index_flicker(self):
        """Index briefly reading extended must not cancel an active right-click."""
        eng = GestureEngine()
        t = 10.0
        down = eng.observe(make_middle_pinch(close=True, index_also_up=False), t)
        self.assertEqual(down.gesture, Gesture.RIGHT_PINCH_DOWN)
        mid = eng.observe(make_middle_pinch(close=True, index_also_up=True), t + 0.05)
        self.assertNotEqual(mid.gesture, Gesture.RIGHT_PINCH_CANCEL)
        self.assertTrue(mid.right_pinched)
        up = eng.observe(make_middle_pinch(close=False, index_also_up=True), t + 0.1)
        self.assertEqual(up.gesture, Gesture.RIGHT_PINCH_UP)

    def test_messy_middle_pinch_still_starts_right(self):
        eng = GestureEngine()
        down = eng.observe(make_middle_pinch(close=True, index_also_up=True), 10.0)
        self.assertEqual(down.gesture, Gesture.RIGHT_PINCH_DOWN)
        self.assertFalse(down.pinched)

    def test_pinch_cancelled_when_palm_opens(self):
        eng = GestureEngine()
        t = 10.0
        eng.observe(make_index_pinch(close=True), t)
        cancel = eng.observe(make_palm_candidate_three(), t + 0.05)
        self.assertEqual(cancel.gesture, Gesture.PINCH_CANCEL)
        self.assertFalse(cancel.pinched)

    def test_lockout_blocks_pinch_after_palm(self):
        eng = GestureEngine()
        t = 10.0
        eng.observe(make_open_palm(), t)
        # Close palm — starts lockout
        eng.observe(make_fist(), t + 0.05)
        # Transient tip contact during lockout must not start pinch
        mid = eng.observe(make_index_pinch(close=True), t + 0.1)
        self.assertEqual(mid.gesture, Gesture.NONE)
        # After lockout expires, pinch works
        after = eng.observe(
            make_index_pinch(close=True), t + 0.05 + config.PALM_PINCH_LOCKOUT + 0.05
        )
        self.assertEqual(after.gesture, Gesture.PINCH_DOWN)


class InteractionArbitrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = InteractionEngine(1920, 1080)
        self.engine.pointing = True
        self.gestures = GestureEngine()
        self.t = 20.0

    def _step(self, hand):
        sig = self.gestures.observe(hand, self.t)
        status, commands = self.engine.update(
            _filtered(),
            Pose.POINT,
            sig,
            _idle_scroll(),
            None,
            (960.0, 540.0),
            self.t,
        )
        self.t += 0.05
        return status, commands, sig

    def test_fist_produces_no_click_or_drag(self):
        clicks = []
        for _ in range(12):
            _, commands, _ = self._step(make_fist(thumb_on_tips=True))
            clicks.extend(
                c
                for c in commands
                if isinstance(c, (Click, RightClick, MouseDown, MouseUp))
            )
        self.assertEqual(clicks, [])

    def test_open_close_palm_produces_no_click(self):
        clicks = []
        for hand in (
            make_fist(),
            make_palm_candidate_three(),
            make_open_palm(),
            make_open_palm(),
            make_open_palm(),
            make_open_palm(),  # dwell
            make_palm_candidate_three(),
            make_fist(),
        ):
            _, commands, _ = self._step(hand)
            clicks.extend(c for c in commands if isinstance(c, (Click, RightClick)))
        self.assertEqual(clicks, [])

    def test_deliberate_pinch_clicks_once(self):
        _, c1, _ = self._step(make_index_pinch(close=True))
        _, c2, _ = self._step(make_index_pinch(close=False))
        all_c = c1 + c2
        self.assertEqual(sum(isinstance(c, Click) for c in all_c), 1)
        self.assertEqual(sum(isinstance(c, RightClick) for c in all_c), 0)

    def test_deliberate_right_pinch(self):
        _, c1, _ = self._step(make_middle_pinch(close=True))
        _, c2, _ = self._step(make_middle_pinch(close=False))
        all_c = c1 + c2
        self.assertEqual(sum(isinstance(c, RightClick) for c in all_c), 1)

    def test_palm_dwell_horizontal_swipe_switches_space(self):
        dwell_frames = int(config.SPACE_PALM_DWELL / 0.05) + 2
        for _ in range(dwell_frames):
            status, commands, _ = self._step(make_open_palm(ox=0.0))
            self.assertEqual(
                sum(isinstance(c, SwitchSpace) for c in commands), 0
            )
        self.assertTrue(status.space_ready)

        # Horizontal swipe past threshold
        status, commands, _ = self._step(make_open_palm(ox=0.08))
        spaces = [c for c in commands if isinstance(c, SwitchSpace)]
        self.assertEqual(len(spaces), 1)
        self.assertEqual(spaces[0].direction, 1)

    def test_palm_dwell_left_swipe_switches_space(self):
        dwell_frames = int(config.SPACE_PALM_DWELL / 0.05) + 2
        for _ in range(dwell_frames):
            self._step(make_open_palm(ox=0.0))
        _, commands, _ = self._step(make_open_palm(ox=-0.08))
        spaces = [c for c in commands if isinstance(c, SwitchSpace)]
        self.assertEqual(len(spaces), 1)
        self.assertEqual(spaces[0].direction, -1)

    def test_palm_can_swipe_left_after_right(self):
        dwell_frames = int(config.SPACE_PALM_DWELL / 0.05) + 2
        for _ in range(dwell_frames):
            self._step(make_open_palm(ox=0.0))
        _, commands, _ = self._step(make_open_palm(ox=0.08))
        self.assertEqual(sum(isinstance(c, SwitchSpace) for c in commands), 1)

        # Advance past cooldown while holding palm at the right end.
        self.t += config.SPACE_SWIPE_COOLDOWN + 0.05
        _, commands, _ = self._step(make_open_palm(ox=0.0))
        spaces = [c for c in commands if isinstance(c, SwitchSpace)]
        self.assertEqual(len(spaces), 1)
        self.assertEqual(spaces[0].direction, -1)

    def test_palm_dwell_vertical_motion_no_space(self):
        dwell_frames = int(config.SPACE_PALM_DWELL / 0.05) + 2
        for _ in range(dwell_frames):
            self._step(make_open_palm(ox=0.0, oy=0.0))
        _, commands, _ = self._step(make_open_palm(ox=0.02, oy=0.10))
        self.assertEqual(sum(isinstance(c, SwitchSpace) for c in commands), 0)

    def test_palm_during_drag_releases_mouse_no_click(self):
        # Start pinch and promote to drag via hold
        self._step(make_index_pinch(close=True))
        hold_frames = int(config.DRAG_ARM_HOLD / 0.05) + 2
        saw_down = False
        for _ in range(hold_frames):
            _, commands, _ = self._step(make_index_pinch(close=True))
            if any(isinstance(c, MouseDown) for c in commands):
                saw_down = True
        self.assertTrue(saw_down)

        _, commands, sig = self._step(make_palm_candidate_three())
        self.assertEqual(sig.gesture, Gesture.PINCH_CANCEL)
        self.assertEqual(sum(isinstance(c, MouseUp) for c in commands), 1)
        self.assertEqual(sum(isinstance(c, Click) for c in commands), 0)


if __name__ == "__main__":
    unittest.main()
