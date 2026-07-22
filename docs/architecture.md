# AirCursor Architecture (v0.16.1)

## Pipeline (implemented)

```text
Camera
  → HandTracker (background MediaPipe VIDEO worker, latest-frame queue)
  → LandmarkFilter (pointer hand tip)
  → hand_landmarks (orientation-invariant finger state)
  → PoseClassifier (pointer hand: peace vs point)
  → ScrollIntentEngine (pointer hand: three-finger scroll)
  → GestureEngine (click hand: pinch / palm families)
  → InteractionEngine
  → ActionDispatcher
  → macOS
Preview: HudRenderer (Spatial Control HUD on the webcam window)
```

---

## Two-hand roles

| Role | Default | Responsibility |
|------|---------|----------------|
| Pointer | `Right` | Peace toggle, index-tip cursor, three-finger scroll |
| Click / Navigate | `Left` | Thumb+index click/drag; thumb+middle right-click; open palm → Spaces |

---

## Click-hand arbitration (palm vs pinch)

Palm and pinch are mutually exclusive. Palm wins immediately.

```text
Neutral
  → PinchCandidate   (ring+pinky curled; thumb nearer index or middle tip)
  → PalmCandidate    (≥3 long fingers extended)
  → Fist             (all curled — never a click)
PalmCandidate / Fist
  → cancel pinch (no Click) + short lockout after palm
PalmCandidate
  → PalmArmed        (full open palm held SPACE_PALM_DWELL)
PalmArmed
  → SpaceSwitch      (horizontal-dominant swipe)
Palm closes
  → Lockout          (PALM_PINCH_LOCKOUT; no new pinches)

Left vs right click uses tip distance with `PINCH_TARGET_MARGIN`. Brief finger
flicker mid-pinch does not cancel — only palm or fist does.
```

- Click is valid only if the gesture stays in the pinch family through release.
- Opening/closing a palm never emits `Click` / `RightClick`.
- If a drag is active when palm opens, emit `MouseUp` (safe release).

---

## Preview HUD

Webcam overlay lives in `hud_renderer.py` (not inline in `main.py`). Chrome is
composited with Pillow (SF Pro type + frosted-glass panels: blur-behind, drop
shadows, hairline borders); on-hand gesture cues stay in OpenCV for speed.

- Top bar: two floating glass islands (brand + tracking, current mode)
- Hand card: POINTER (right) with eyebrow + status + guidance
- Gesture overlays: cursor ring, scroll band + rubber-band, pinch lines, palm swipe
- Palm swipe overlay: dwell progress, anchor-to-palm rubber-band, live direction
- Left gesture feed: last 10 recognized actions, newest at top; animated
  downward stack with fade/slide entry and bottom exit
- `H` toggles chrome; `D` toggles landmark/geometry debug (`HUD_SHOW_DEBUG`)

---

## Finger geometry

Finger extended/curled uses MCP→PIP→TIP alignment in landmark space (`x,y,z`),
not screen-Y. Peace = index+middle extended, ring+pinky curled. Scroll =
index+middle+ring extended, pinky curled.

---

## Scroll (pointer hand)

1. Hold **index + middle + ring** for `SCROLL_INTENT_DWELL`.
2. Pull hand up/down from anchor — rubber-band incremental scroll.
3. Cursor movement suppressed while scroll intent is active.
4. `ScrollIntentSignal` exposes `dwell_progress`, `anchor`, and `centroid` for the HUD.

---

## Spaces (click hand)

1. Detect palm candidate (≥3 fingers) — suppress pinch.
2. Hold full open palm for `SPACE_PALM_DWELL`.
3. Swipe horizontally (`|dx| ≥ SPACE_SWIPE_THRESHOLD` and
   `|dx| ≥ SPACE_SWIPE_AXIS_RATIO × |dy|`).
4. Brief `SPACE_PALM_GRACE` only for landmark dropout while armed.

---

## Next

- Multi-monitor clamp
- CI for `tests/`
