# AirCursor Architecture (v0.16.1)

AirCursor turns webcam hand landmarks into macOS cursor, click, scroll, and
Spaces input. Policy lives in Python engines; OS I/O is isolated in one
dispatcher. The preview HUD is a separate render path over the same signals.

## Goals

- Two-hand control that feels intentional: pointer aims, click hand clicks.
- Keep the webcam preview responsive while MediaPipe runs.
- Avoid false clicks from fists or palm open/close transitions.
- Make gesture state visible in the HUD for debugging and learning.

## Layering

```text
Camera
  → HandTracker          # landmarks only (async MediaPipe VIDEO)
  → LandmarkFilter       # tip smooth + active-region gate (pointer)
  → hand_landmarks       # shared finger geometry
  → PoseClassifier       # pointer: peace vs point
  → ScrollIntentEngine   # pointer: three-finger scroll
  → GestureEngine        # click: pinch / palm families
  → InteractionEngine    # state → commands (no Quartz)
  → ActionDispatcher     # Quartz / AppKit only
Preview: HudRenderer     # Spatial Control overlay on the webcam frame
```

`main.py` wires the loop. Engines do not import each other across the
policy/I/O boundary: `InteractionEngine` never talks to Quartz;
`ActionDispatcher` never decides gestures.

## Components

| Module | Responsibility |
|--------|----------------|
| `camera.py` | Capture frames; no CV logic |
| `hand_tracker.py` | MediaPipe Hand Landmarker; role resolve; control-point tip |
| `hand_landmarks.py` | Orientation-invariant extended/curled finger tests |
| `landmark_filter.py` | One Euro filter on pointer tip; active tracking region |
| `pose_classifier.py` | Stateless peace / point (and related) labels |
| `scroll_intent_engine.py` | Dwell + rubber-band scroll signal for the pointer hand |
| `gesture_engine.py` | Click-hand pinch, right-pinch, palm candidate / open palm |
| `interaction_engine.py` | Cursor mode, click/drag, scroll, Spaces; emits commands |
| `action_dispatcher.py` | Warp cursor, mouse, scroll wheel, Ctrl+Arrow Spaces |
| `hud_renderer.py` | Frosted chrome (Pillow) + on-hand cues (OpenCV) |
| `config.py` | All tunables |

## Hand roles

| Role | Default | Responsibility |
|------|---------|----------------|
| Pointer | `Right` | Peace toggle, index-tip cursor, three-finger scroll |
| Click / Navigate | `Left` | Thumb+index click/drag; thumb+middle right-click; open palm → Spaces |

Frames are mirrored for a selfie view. `SWAP_HANDEDNESS_FOR_MIRROR` maps
MediaPipe labels to the user's left/right.

## Async inference

MediaPipe `VIDEO` runs on a background worker. Frames are downscaled to
`INFERENCE_WIDTH` × `INFERENCE_HEIGHT` (landmarks stay normalized). A
one-slot latest-frame queue drops stale work so capture and HUD are not
blocked by inference latency.

## Click-hand arbitration (palm vs pinch)

Palm and pinch are mutually exclusive. Palm wins immediately.

```text
Neutral
  → PinchCandidate   (ring+pinky curled; thumb nearer index or middle tip)
  → PalmCandidate    (≥3 long fingers extended)
  → Fist             (all curled; never a click)
PalmCandidate / Fist
  → cancel pinch (no Click) + short lockout after palm
PalmCandidate
  → PalmArmed        (full open palm held SPACE_PALM_DWELL)
PalmArmed
  → SpaceSwitch      (horizontal-dominant swipe)
Palm closes
  → Lockout          (PALM_PINCH_LOCKOUT; no new pinches)
```

- Left vs right click uses tip distance with `PINCH_TARGET_MARGIN`.
- Brief finger flicker mid-pinch does not cancel; only palm or fist does.
- Click is valid only if the gesture stays in the pinch family through release.
- Opening/closing a palm never emits `Click` / `RightClick`.
- If a drag is active when palm opens, emit `MouseUp` (safe release).

## Commands

`InteractionEngine` emits typed commands; `main` dispatches them:

| Command | Meaning |
|---------|---------|
| `SetCursor` | Warp to screen coords |
| `Click` / `RightClick` | Atomic down+up |
| `MouseDown` / `MouseUp` | Drag start / end |
| `Scroll` | Pixel wheel deltas |
| `SwitchSpace` | `-1` previous / `+1` next (Ctrl+Arrow) |

## Finger geometry

Extended/curled uses MCP→PIP→TIP alignment in landmark space (`x,y,z`), not
screen-Y.

- Peace: index + middle extended; ring + pinky curled
- Scroll: index + middle + ring extended; pinky curled

## Scroll (pointer hand)

1. Hold index + middle + ring for `SCROLL_INTENT_DWELL`.
2. Pull up/down from anchor: rubber-band incremental scroll.
3. Cursor movement is suppressed while scroll intent is active.
4. `ScrollIntentSignal` exposes `dwell_progress`, `anchor`, and `centroid` for the HUD.

## Spaces (click hand)

1. Palm candidate (≥3 fingers) suppresses pinch.
2. Hold full open palm for `SPACE_PALM_DWELL`.
3. Swipe when `|dx| ≥ SPACE_SWIPE_THRESHOLD` and
   `|dx| ≥ SPACE_SWIPE_AXIS_RATIO × |dy|`.
4. `SPACE_PALM_GRACE` tolerates brief landmark dropout while armed.
5. After a switch, re-arm so the opposite swipe can fire without closing the palm.

## Preview HUD

`hud_renderer.py` owns the overlay (not `main.py`).

- Chrome: Pillow (SF Pro, frosted panels, blur-behind)
- On-hand cues: OpenCV (speed)
- Top bar: brand/tracking island + mode island
- Hand card: POINTER status + guidance
- Overlays: cursor ring, scroll rubber-band, pinch lines, palm swipe progress
- Left feed: last 10 actions, newest at top (slide/fade)
- `H` toggles chrome; `D` toggles landmark/geometry debug (`HUD_SHOW_DEBUG`)

## Design decisions

| Decision | Why |
|----------|-----|
| Policy vs I/O split | Engines stay testable without Quartz; dispatcher stays dumb |
| Async latest-frame inference | Preview stays live when MediaPipe is slow |
| Palm wins over pinch | Fist/palm transitions must not fire clicks |
| Orientation-invariant fingers | Poses work with tilted hands, not only upright screen-Y |
| Speed-scaled cursor gain | Slow tips for aiming; faster motion for travel |
| HUD chrome on Pillow | Readable type and real glass; cues stay cheap in OpenCV |

## Limitations

- macOS only (Quartz / AppKit).
- Cursor clamp uses the main screen size; multi-monitor is not handled.
- Requires Accessibility for the process that launches AirCursor.
- Two-hand tracking cost still dominates; inference is async but not free.

## Next

- Multi-monitor clamp
- CI for `tests/`
