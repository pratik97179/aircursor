"""Spatial Control HUD — frosted-glass webcam overlay with SF Pro typography.

Chrome (top bar, hand cards, gesture feed) is composited with Pillow so we get
real anti-aliased type and true blur-behind glass instead of OpenCV's stroke
font and flat alpha. On-hand gesture cues stay in OpenCV for speed.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import os
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

import config
from hand_landmarks import finger_states
from pose_classifier import Pose


# --- palette (RGB) -----------------------------------------------------------

INK = (10, 12, 16)
WHITE = (244, 246, 251)
MUTED = (150, 157, 170)
FAINT = (105, 112, 126)
LINE = (255, 255, 255)

GREEN = (74, 222, 128)
ORANGE = (251, 146, 60)
CYAN = (34, 211, 238)
MAGENTA = (232, 121, 249)
PURPLE = (167, 139, 250)
RED = (248, 113, 113)
BLUE = (96, 165, 250)

_FEED_LIMIT = 10
_FEED_ROW_HEIGHT = 34
_FEED_ROW_GAP = 6
_FEED_ENTER_DURATION = 0.24
_FEED_EXIT_DURATION = 0.38
_TIP_INDEX = 8
_TIP_MIDDLE = 12
_TIP_RING = 16
_TIP_THUMB = 4
_FINGER_TIPS = {"index": 8, "middle": 12, "ring": 16, "pinky": 20, "thumb_open": 4}

_FONT_CANDIDATES = (
    "/System/Library/Fonts/SFNS.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
)


@dataclass
class _FeedItem:
    text: str
    color: tuple[int, int, int]
    born: float
    y: float | None = None
    exiting_at: float | None = None


def _bgr(rgb):
    return (int(rgb[2]), int(rgb[1]), int(rgb[0]))


def _pt(hand, idx, width, height):
    lm = hand[idx]
    return int(lm.x * width), int(lm.y * height)


def _norm_pt(xy, width, height):
    if xy is None:
        return None
    return int(xy[0] * width), int(xy[1] * height)


def _lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class _FontBook:
    """Cache SF Pro (variable) faces by size + weight, with graceful fallback."""

    def __init__(self):
        self._cache = {}
        self._path = next((p for p in _FONT_CANDIDATES if os.path.exists(p)), None)
        self._variable = bool(self._path and self._path.endswith("SFNS.ttf"))

    def get(self, size, weight="Regular"):
        key = (size, weight)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        font = None
        if self._path is not None:
            try:
                font = ImageFont.truetype(self._path, size)
                if self._variable:
                    try:
                        font.set_variation_by_name(weight)
                    except Exception:
                        pass
            except Exception:
                font = None
        if font is None:
            font = ImageFont.load_default()
        self._cache[key] = font
        return font


class HudRenderer:
    """Draw the Spatial Control HUD onto a BGR frame."""

    def __init__(self):
        self.show_chrome = bool(getattr(config, "HUD_ENABLED", True))
        self.show_debug = bool(getattr(config, "HUD_SHOW_DEBUG", False))
        self._fonts = _FontBook()
        self._feed: list[_FeedItem] = []
        self._prev_pointing = False
        self._prev_right = False
        self._prev_dragging = False
        self._prev_scroll_armed = False
        self._prev_space_ready = False
        self._palm_trail: list[tuple[int, int]] = []
        self._t0 = time.monotonic()

    # --- public API ----------------------------------------------------------

    def toggle_chrome(self):
        self.show_chrome = not self.show_chrome

    def toggle_debug(self):
        self.show_debug = not self.show_debug

    def note_action(self, text, color=WHITE, now=None):
        if now is None:
            now = time.monotonic()
        # Collapse duplicate state noise while preserving repeated real actions.
        if (
            self._feed
            and self._feed[-1].text == text
            and now - self._feed[-1].born < 0.25
        ):
            return

        active = [item for item in self._feed if item.exiting_at is None]
        if len(active) >= _FEED_LIMIT:
            active[0].exiting_at = now
        self._feed.append(_FeedItem(text=text, color=color, born=now))

    def render(
        self,
        frame,
        *,
        pointer_hand,
        click_hand,
        status,
        click_signal,
        scroll_signal,
        hand_count,
        tip,
        now,
        detection_result=None,
        tracker=None,
    ):
        pulse = 0.5 + 0.5 * math.sin((now - self._t0) * 4.0)
        self._update_feed_edges(status, click_signal, now)

        # On-hand gesture cues (OpenCV, BGR) — fast, drawn under chrome.
        if self.show_debug:
            if tracker is not None and detection_result is not None:
                if detection_result.hand_landmarks:
                    frame = tracker.draw_landmarks(frame, detection_result)
            self._draw_geometry_tips(frame, pointer_hand)
            self._draw_geometry_tips(frame, click_hand)

        self._draw_gesture_overlays(
            frame,
            pointer_hand=pointer_hand,
            click_hand=click_hand,
            status=status,
            click_signal=click_signal,
            scroll_signal=scroll_signal,
            tip=tip,
            pulse=pulse,
        )

        if not self.show_chrome:
            return frame

        # Chrome (Pillow) — frosted glass + SF Pro type.
        base = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        self._draw_top_bar(base, draw, status, hand_count, pulse)
        self._draw_hand_cards(
            base,
            draw,
            pointer_hand=pointer_hand,
            status=status,
            scroll_signal=scroll_signal,
            pulse=pulse,
        )
        self._draw_gesture_feed(draw, base.size, now)

        base.alpha_composite(overlay)
        return cv2.cvtColor(np.array(base.convert("RGB")), cv2.COLOR_RGB2BGR)

    # --- glass primitives (Pillow) -------------------------------------------

    def _shadow(self, base, box, radius, blur=14, alpha=120, dy=8):
        x1, y1, x2, y2 = box
        pad = blur * 3
        w = (x2 - x1) + pad * 2
        h = (y2 - y1) + pad * 2
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle(
            [pad, pad + dy, pad + (x2 - x1), pad + dy + (y2 - y1)],
            radius=radius,
            fill=(0, 0, 0, alpha),
        )
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
        base.alpha_composite(layer, (x1 - pad, y1 - pad))

    def _frost(self, base, box, radius, blur=9, dim=0.52):
        x1, y1, x2, y2 = box
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(base.width, x2), min(base.height, y2)
        if x2 <= x1 or y2 <= y1:
            return
        crop = base.crop((x1, y1, x2, y2)).filter(ImageFilter.GaussianBlur(blur))
        crop = ImageEnhance.Brightness(crop).enhance(dim)
        crop = ImageEnhance.Color(crop).enhance(0.85)
        mask = Image.new("L", crop.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, crop.size[0] - 1, crop.size[1] - 1], radius=radius, fill=255
        )
        base.paste(crop, (x1, y1), mask)

    def _panel(self, base, draw, box, radius=16, accent=None, shadow=True):
        if shadow:
            self._shadow(base, box, radius)
        self._frost(base, box, radius)
        x1, y1, x2, y2 = box
        # hairline border
        draw.rounded_rectangle(box, radius=radius, outline=(*LINE, 42), width=1)
        # top sheen
        draw.rounded_rectangle(
            [x1 + 1, y1 + 1, x2 - 1, y1 + (y2 - y1) // 2],
            radius=radius,
            outline=None,
            fill=(255, 255, 255, 10),
        )
        if accent is not None:
            draw.rounded_rectangle(
                [x1, y1, x2, y2], radius=radius, outline=(*accent, 90), width=1
            )

    def _measure(self, text, font, tracking=0.0):
        if not text:
            return 0.0
        w = sum(font.getlength(ch) for ch in text)
        return w + tracking * (len(text) - 1)

    def _text(self, draw, xy, text, font, fill, anchor="lm", tracking=0.0):
        if tracking <= 0:
            draw.text(xy, text, font=font, fill=(*fill, 255), anchor=anchor)
            return
        x, y = xy
        for ch in text:
            draw.text((x, y), ch, font=font, fill=(*fill, 255), anchor="lm")
            x += font.getlength(ch) + tracking

    def _dot(self, draw, center, r, color, glow=True):
        cx, cy = center
        if glow:
            draw.ellipse(
                [cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3], fill=(*color, 55)
            )
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, 255))

    # --- top bar -------------------------------------------------------------

    def _mode_label(self, status):
        if not status.pointing:
            return "Idle", MUTED
        if status.right_clicked:
            return "Right click", MAGENTA
        if status.switching_space:
            return "Space", PURPLE
        if status.space_ready:
            return "Palm swipe", PURPLE
        if getattr(status, "space_dwelling", False):
            return "Palm hold", PURPLE
        if status.dragging:
            return "Dragging", CYAN
        if status.scrolling or status.scroll_armed:
            return "Scrolling", ORANGE
        if status.scroll_dwelling:
            return "Scroll hold", ORANGE
        if status.pinched:
            return "Pinch", CYAN
        if status.pose == Pose.SYSTEM:
            return "Peace", GREEN
        return "Cursor mode", GREEN

    def _tracking(self, hand_count):
        if hand_count <= 0:
            return "No hands", RED
        if hand_count == 1:
            return "1 hand", BLUE
        return "Tracking", GREEN

    def _draw_top_bar(self, base, draw, status, hand_count, pulse):
        w = base.width
        y1, h = 14, 46
        y2 = y1 + h
        cy = y1 + h // 2

        brand_font = self._fonts.get(21, "Bold")
        chip_font = self._fonts.get(14, "Semibold")

        # Left island: brand + tracking
        track_label, track_color = self._tracking(hand_count)
        brand = "AirCursor"
        pad = 16
        gap = 12
        brand_w = self._measure(brand, brand_font)
        track_w = self._measure(track_label.upper(), chip_font, tracking=1.0)
        left_x1 = 16
        dot_r = 4
        content = dot_r * 2 + 8 + brand_w + gap + 1 + gap + track_w
        left_x2 = int(left_x1 + pad + content + pad)
        self._panel(base, draw, (left_x1, y1, left_x2, y2), radius=14, shadow=True)

        x = left_x1 + pad
        live = _lerp(track_color, WHITE, 0.4 * pulse) if hand_count >= 2 else track_color
        self._dot(draw, (x + dot_r, cy), dot_r, live)
        x += dot_r * 2 + 8
        self._text(draw, (x, cy), brand, brand_font, WHITE, anchor="lm")
        x += brand_w + gap
        draw.line([(x, cy - 9), (x, cy + 9)], fill=(*LINE, 45), width=1)
        x += gap
        self._text(
            draw, (x, cy), track_label.upper(), chip_font, track_color, tracking=1.0
        )

        # Right island: current mode
        mode_label, mode_color = self._mode_label(status)
        mode_w = self._measure(mode_label.upper(), chip_font, tracking=1.0)
        right_x2 = w - 16
        rc = dot_r * 2 + 10 + mode_w
        right_x1 = int(right_x2 - pad - rc - pad)
        self._panel(
            base, draw, (right_x1, y1, right_x2, y2), radius=14, accent=mode_color
        )
        mx = right_x1 + pad
        mdot = _lerp(mode_color, WHITE, 0.4 * pulse) if status.pointing else mode_color
        self._dot(draw, (mx + dot_r, cy), dot_r, mdot)
        mx += dot_r * 2 + 10
        self._text(
            draw, (mx, cy), mode_label.upper(), chip_font, mode_color, tracking=1.0
        )

    # --- hand cards ----------------------------------------------------------

    def _pointer_lines(self, pointer_hand, status, scroll_signal):
        if pointer_hand is None:
            return "Not visible", "Show your right hand", FAINT
        if not status.pointing:
            if status.pose == Pose.SYSTEM:
                return "Peace held", "Hold to enable cursor", GREEN
            return "Standby", "Peace sign to enable", MUTED
        if status.scroll_dwelling:
            p = int(100 * float(getattr(scroll_signal, "dwell_progress", 0.0) or 0.0))
            return "Scroll arming", f"Hold steady · {p}%", ORANGE
        if status.scrolling:
            return "Scrolling", "Pull up or down", ORANGE
        if status.scroll_armed:
            return "Scroll ready", "Pull up or down", ORANGE
        if status.pose == Pose.SYSTEM:
            return "Peace held", "Hold to exit", GREEN
        return "Cursor mode", "Index tip is steering", GREEN

    def _draw_hand_cards(
        self,
        base,
        draw,
        *,
        pointer_hand,
        status,
        scroll_signal,
        pulse,
    ):
        w, h = base.width, base.height
        card_w, card_h = 262, 84
        margin = 18
        y1 = h - margin - card_h
        y2 = h - margin

        p_status, p_hint, p_accent = self._pointer_lines(
            pointer_hand, status, scroll_signal
        )

        self._card(
            base, draw,
            (w - margin - card_w, y1, w - margin, y2),
            eyebrow="RIGHT · POINTER",
            status_text=p_status,
            hint=p_hint,
            accent=p_accent,
            active=pointer_hand is not None,
            pulse=pulse,
        )

    def _card(self, base, draw, box, eyebrow, status_text, hint, accent, active, pulse):
        x1, y1, x2, y2 = box
        self._panel(base, draw, box, radius=16, accent=accent if active else None)

        # Accent rail
        rail = accent if active else FAINT
        draw.rounded_rectangle(
            [x1 + 12, y1 + 16, x1 + 15, y2 - 16], radius=2, fill=(*rail, 230)
        )

        eb_font = self._fonts.get(11, "Semibold")
        st_font = self._fonts.get(19, "Semibold")
        hn_font = self._fonts.get(13, "Regular")

        tx = x1 + 26
        self._text(draw, (tx, y1 + 20), eyebrow, eb_font, MUTED, tracking=1.5)
        self._text(draw, (tx, y1 + 44), status_text, st_font, WHITE, anchor="lm")
        self._text(draw, (tx, y1 + 66), hint, hn_font, MUTED, anchor="lm")

        # Status dot top-right
        r = 5
        col = _lerp(accent, WHITE, 0.35 * pulse) if active else FAINT
        self._dot(draw, (x2 - 20, y1 + 22), r, col, glow=active)

    # --- gesture feed --------------------------------------------------------

    def _draw_gesture_feed(self, draw, size, now):
        """Newest enters at top; old rows descend and fade/slide out below."""
        width, height = size

        self._feed = [
            item
            for item in self._feed
            if item.exiting_at is None
            or now - item.exiting_at < _FEED_EXIT_DURATION
        ]
        active = [item for item in self._feed if item.exiting_at is None]
        exiting = [item for item in self._feed if item.exiting_at is not None]

        top = 78
        row_step = _FEED_ROW_HEIGHT + _FEED_ROW_GAP
        x = 18
        row_width = 224
        font = self._fonts.get(13, "Semibold")
        meta_font = self._fonts.get(9, "Semibold")

        for index, item in enumerate(active):
            # Feed is stored oldest→newest. Newest targets the first row.
            target_y = (
                top
                + (len(active) - 1 - index) * row_step
                + _FEED_ROW_HEIGHT
            )
            if item.y is None:
                item.y = target_y - 14
            item.y += (target_y - item.y) * 0.24

            enter = min(
                1.0, max(0.0, (now - item.born) / _FEED_ENTER_DURATION)
            )
            # Older rows are progressively quieter, like a game kill feed.
            age_rank = index / max(1, len(active) - 1)
            rank_alpha = 0.46 + 0.54 * age_rank
            alpha = enter * rank_alpha
            slide_x = int(x - (1.0 - enter) * 18)
            self._draw_feed_row(
                draw,
                slide_x,
                int(item.y),
                row_width,
                item,
                alpha,
                font,
                meta_font,
            )

        # The displaced oldest row exits below/left while the stack shifts down.
        bottom_target = (
            top + max(0, len(active) - 1) * row_step + _FEED_ROW_HEIGHT
        )
        for item in exiting:
            progress = min(
                1.0, max(0.0, (now - item.exiting_at) / _FEED_EXIT_DURATION)
            )
            if item.y is None:
                item.y = bottom_target
            y = int(item.y + progress * 18)
            slide_x = int(x - progress * 28)
            self._draw_feed_row(
                draw,
                slide_x,
                y,
                row_width,
                item,
                (1.0 - progress) * 0.42,
                font,
                meta_font,
            )

    def _draw_feed_row(
        self, draw, x, y, width, item, alpha, font, meta_font
    ):
        alpha = max(0.0, min(1.0, alpha))
        if alpha <= 0.01:
            return
        height = _FEED_ROW_HEIGHT
        a = int(255 * alpha)
        box = (x, y - height, x + width, y)
        draw.rounded_rectangle(
            box,
            radius=10,
            fill=(8, 10, 14, int(150 * alpha)),
            outline=(*item.color, int(78 * alpha)),
            width=1,
        )
        draw.rounded_rectangle(
            (x + 8, y - height + 8, x + 11, y - 8),
            radius=2,
            fill=(*item.color, a),
        )
        draw.text(
            (x + 20, y - height // 2),
            item.text,
            font=font,
            fill=(*item.color, a),
            anchor="lm",
        )
        draw.text(
            (x + width - 10, y - height // 2),
            "GESTURE",
            font=meta_font,
            fill=(*MUTED, int(150 * alpha)),
            anchor="rm",
        )

    # --- on-hand gesture cues (OpenCV) ---------------------------------------

    def _glow_ring(self, frame, center, radius, rgb, strength=0.32, rings=3):
        color = _bgr(rgb)
        overlay = frame.copy()
        for i in range(rings, 0, -1):
            cv2.circle(overlay, center, radius + i * 4, color, 1, cv2.LINE_AA)
        cv2.addWeighted(overlay, strength, frame, 1.0 - strength, 0, frame)
        cv2.circle(frame, center, radius, color, 2, cv2.LINE_AA)

    def _glow_line(self, frame, a, b, rgb, thick=2, strength=0.3):
        color = _bgr(rgb)
        overlay = frame.copy()
        cv2.line(overlay, a, b, color, thick + 4, cv2.LINE_AA)
        cv2.addWeighted(overlay, strength, frame, 1.0 - strength, 0, frame)
        cv2.line(frame, a, b, color, thick, cv2.LINE_AA)

    def _draw_geometry_tips(self, frame, hand):
        if hand is None:
            return
        h, w = frame.shape[:2]
        states = finger_states(hand)
        colors = {
            "index": GREEN,
            "middle": CYAN,
            "ring": ORANGE,
            "pinky": PURPLE,
            "thumb_open": RED,
        }
        for name, tip_i in _FINGER_TIPS.items():
            if states.get(name):
                x, y = _pt(hand, tip_i, w, h)
                cv2.circle(frame, (x, y), 5, _bgr(colors[name]), -1, cv2.LINE_AA)

    def _draw_gesture_overlays(
        self,
        frame,
        *,
        pointer_hand,
        click_hand,
        status,
        click_signal,
        scroll_signal,
        tip,
        pulse,
    ):
        h, w = frame.shape[:2]

        if pointer_hand is not None and status.pose == Pose.SYSTEM:
            a = _pt(pointer_hand, _TIP_INDEX, w, h)
            b = _pt(pointer_hand, _TIP_MIDDLE, w, h)
            mid = ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2 - 20)
            self._glow_line(frame, a, mid, GREEN, 2, 0.25 + 0.1 * pulse)
            self._glow_line(frame, b, mid, GREEN, 2, 0.25 + 0.1 * pulse)
            self._glow_ring(frame, a, 6, GREEN, 0.22)
            self._glow_ring(frame, b, 6, GREEN, 0.22)

        if status.pointing and pointer_hand is not None:
            if status.scroll_dwelling or status.scroll_armed or status.scrolling:
                self._draw_scroll_overlay(frame, pointer_hand, scroll_signal, status, pulse)
            elif tip is not None:
                p = _norm_pt(tip, w, h)
                if p is not None:
                    r = 12 + int(3 * pulse)
                    self._glow_ring(frame, p, r, GREEN, 0.26 + 0.12 * pulse)
                    cv2.circle(frame, p, 3, _bgr(WHITE), -1, cv2.LINE_AA)

        if click_hand is not None and status.pointing:
            palmish = (
                getattr(click_signal, "palm_candidate", False)
                or click_signal.open_palm
                or status.space_ready
                or getattr(status, "space_dwelling", False)
                or status.switching_space
            )
            if palmish:
                # Palm family owns the hand — never show pinch connectors.
                self._draw_palm_overlay(
                    frame, click_hand, click_signal, status, pulse
                )
            elif click_signal.pinched or status.dragging:
                self._draw_pinch_line(frame, click_hand, _TIP_THUMB, _TIP_INDEX, CYAN)
            elif click_signal.right_pinched or status.right_clicked:
                self._draw_pinch_line(frame, click_hand, _TIP_THUMB, _TIP_MIDDLE, MAGENTA)
            else:
                self._palm_trail.clear()

    def _draw_scroll_overlay(self, frame, hand, scroll_signal, status, pulse):
        h, w = frame.shape[:2]
        i = _pt(hand, _TIP_INDEX, w, h)
        m = _pt(hand, _TIP_MIDDLE, w, h)
        r = _pt(hand, _TIP_RING, w, h)
        color = _bgr(ORANGE)

        pts = np.array([i, m, r], dtype=np.int32)
        overlay = frame.copy()
        cv2.fillPoly(overlay, [pts], color, cv2.LINE_AA)
        alpha = 0.14 + (0.08 * pulse if status.scroll_dwelling else 0.04)
        cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0, frame)
        cv2.polylines(frame, [pts], True, color, 2, cv2.LINE_AA)
        for p in (i, m, r):
            cv2.circle(frame, p, 4, color, -1, cv2.LINE_AA)

        if status.scroll_armed or status.scrolling:
            anchor = _norm_pt(scroll_signal.anchor, w, h)
            centroid = _norm_pt(scroll_signal.centroid, w, h)
            if anchor is not None and centroid is not None:
                self._glow_ring(frame, anchor, 6, ORANGE, 0.2)
                self._glow_line(frame, anchor, centroid, ORANGE, 2, 0.35)
                cv2.circle(frame, centroid, 7, color, -1, cv2.LINE_AA)
                cv2.circle(frame, centroid, 7, _bgr(WHITE), 1, cv2.LINE_AA)
                dy = centroid[1] - anchor[1]
                if abs(dy) > 6:
                    tip_y = centroid[1] + (18 if dy > 0 else -18)
                    cv2.arrowedLine(
                        frame, centroid, (centroid[0], tip_y), color, 2,
                        cv2.LINE_AA, tipLength=0.4,
                    )

    def _draw_pinch_line(self, frame, hand, a_i, b_i, rgb, thick=2):
        h, w = frame.shape[:2]
        a = _pt(hand, a_i, w, h)
        b = _pt(hand, b_i, w, h)
        self._glow_line(frame, a, b, rgb, thick, 0.35)
        for p in (a, b):
            cv2.circle(frame, p, 5, _bgr(rgb), -1, cv2.LINE_AA)
            cv2.circle(frame, p, 5, _bgr(WHITE), 1, cv2.LINE_AA)

    def _draw_palm_overlay(self, frame, hand, click_signal, status, pulse):
        h, w = frame.shape[:2]
        tips = [_pt(hand, i, w, h) for i in (4, 8, 12, 16, 20)]
        pts = np.array(tips, dtype=np.int32)
        hull = cv2.convexHull(pts)
        overlay = frame.copy()
        cv2.fillConvexPoly(overlay, hull, _bgr(PURPLE), cv2.LINE_AA)
        a = 0.10 + 0.04 * pulse
        cv2.addWeighted(overlay, a, frame, 1.0 - a, 0, frame)
        cv2.polylines(frame, [hull], True, _bgr(PURPLE), 2, cv2.LINE_AA)

        palm = click_signal.palm_point
        if palm is None:
            self._palm_trail.clear()
            return
        p = _norm_pt(palm, w, h)
        if p is None:
            return

        if status.space_dwelling:
            # Arming: progress bar under the palm, like scroll dwell.
            progress = max(
                0.0, min(1.0, status.space_dwell_progress)
            )
            bar_w, bar_h = 88, 5
            x1 = p[0] - bar_w // 2
            y1 = p[1] + 30
            cv2.rectangle(
                frame,
                (x1, y1),
                (x1 + bar_w, y1 + bar_h),
                _bgr(FAINT),
                -1,
                cv2.LINE_AA,
            )
            fill = int(bar_w * progress)
            if fill:
                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x1 + fill, y1 + bar_h),
                    _bgr(PURPLE),
                    -1,
                    cv2.LINE_AA,
                )
            self._glow_ring(
                frame, p, 8 + int(3 * pulse), PURPLE, 0.25
            )
            return

        anchor = _norm_pt(status.space_anchor, w, h)
        current = _norm_pt(status.space_palm, w, h)
        if status.space_ready and anchor is not None and current is not None:
            # Armed: horizontal rubber band from anchor to live palm.
            self._glow_ring(frame, anchor, 6, PURPLE, 0.2)
            self._glow_line(frame, anchor, current, PURPLE, 2, 0.35)
            cv2.circle(
                frame, current, 7, _bgr(PURPLE), -1, cv2.LINE_AA
            )
            cv2.circle(
                frame, current, 7, _bgr(WHITE), 1, cv2.LINE_AA
            )
            dx = current[0] - anchor[0]
            if abs(dx) > 6:
                arrow_x = current[0] + (20 if dx > 0 else -20)
                cv2.arrowedLine(
                    frame,
                    current,
                    (arrow_x, current[1]),
                    _bgr(PURPLE),
                    2,
                    cv2.LINE_AA,
                    tipLength=0.4,
                )
            return

        # Candidate before full dwell: neutral two-way affordance.
        self._glow_ring(frame, p, 8, PURPLE, 0.25)
        span = 28
        cv2.arrowedLine(
            frame,
            p,
            (p[0] + span, p[1]),
            _bgr(PURPLE),
            2,
            cv2.LINE_AA,
            tipLength=0.4,
        )
        cv2.arrowedLine(
            frame,
            p,
            (p[0] - span, p[1]),
            _bgr(PURPLE),
            2,
            cv2.LINE_AA,
            tipLength=0.4,
        )

    # --- feed state edges ----------------------------------------------------

    def _update_feed_edges(self, status, click_signal, now):
        if status.pointing and not self._prev_pointing:
            self.note_action("CURSOR ON", GREEN, now)
        elif not status.pointing and self._prev_pointing:
            self.note_action("CURSOR OFF", MUTED, now)
        if status.right_clicked and not self._prev_right:
            self.note_action("RIGHT CLICK", MAGENTA, now)
        if status.dragging and not self._prev_dragging:
            self.note_action("DRAG", CYAN, now)
        scroll_armed = status.scroll_armed or status.scrolling
        if scroll_armed and not self._prev_scroll_armed:
            self.note_action("SCROLL ARMED", ORANGE, now)
        if status.space_ready and not self._prev_space_ready:
            self.note_action("PALM ARMED", PURPLE, now)

        self._prev_pointing = status.pointing
        self._prev_right = status.right_clicked
        self._prev_dragging = status.dragging
        self._prev_scroll_armed = scroll_armed
        self._prev_space_ready = status.space_ready
