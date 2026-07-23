# AirCursor

Hands-free macOS cursor control from a laptop webcam, using MediaPipe hand
tracking.

**v0.16.1**: Spatial Control HUD, palm/pinch/fist arbitration, and background
hand inference so the preview stays responsive. Built in public; see
[CHANGELOG.md](CHANGELOG.md).

## Gestures

| Hand (default) | Gesture | Action |
|----------------|---------|--------|
| **Right** (pointer) | Peace, hold briefly | Toggle Cursor Mode |
| **Right** | Index tip (Cursor Mode on) | Move cursor |
| **Right** | Index + middle + ring, hold then pull | Scroll |
| **Left** (click) | Thumb + index pinch | Click; hold + move to drag |
| **Left** | Thumb + middle pinch | Right-click |
| **Left** | Open palm hold, then swipe L/R | Switch macOS Spaces |

Roles are mirrored to match how you see yourself on camera. Swap
`POINTER_HANDEDNESS` / `CLICK_HANDEDNESS` in `src/config.py` if needed.

Palm and pinch are mutually exclusive: opening a palm cancels a pending pinch
instead of emitting a click.

## Requirements

- macOS (tested on Apple Silicon with the built-in FaceTime camera)
- Python 3.14+
- [uv](https://github.com/astral-sh/uv)
- `models/hand_landmarker.task` (shipped in this repo)
- **Accessibility** permission for the terminal or IDE that runs AirCursor  
  (System Settings → Privacy & Security → Accessibility)

Without Accessibility, the preview can run but cursor move and clicks will fail.

## Run

From the repository root:

```bash
uv sync
uv run aircursor
```

Or:

```bash
uv run python src/main.py
```

Preview window keys:

| Key | Action |
|-----|--------|
| `q` | Quit |
| `h` | Toggle HUD chrome |
| `d` | Toggle landmark / geometry debug |

## Configuration

All tunables live in [`src/config.py`](src/config.py). Common knobs:

| Area | Examples |
|------|----------|
| Camera / inference | `CAMERA_*`, `INFERENCE_WIDTH` / `HEIGHT` |
| Hand roles | `POINTER_HANDEDNESS`, `CLICK_HANDEDNESS` |
| Pinch / click / drag | `PINCH_ENTER`, `DRAG_SLOP`, `DRAG_ARM_HOLD` |
| Scroll | `SCROLL_INTENT_DWELL`, `SCROLL_RUBBER_*`, `SCROLL_NATURAL` |
| Spaces swipe | `SPACE_PALM_DWELL`, `SPACE_SWIPE_THRESHOLD` |
| Cursor feel | `CURSOR_GAIN_*`, `ONE_EURO_*` |
| HUD defaults | `HUD_ENABLED`, `HUD_SHOW_DEBUG` |

## Tests

```bash
uv run python -m unittest discover -s tests -v
```

Current coverage focuses on click-hand palm/pinch arbitration and Spaces
dwell / axis gating (`tests/test_gesture_arbitration.py`).

## Tech stack

- **Python** + **uv**
- **OpenCV**: webcam capture
- **Pillow**: Spatial Control HUD (SF Pro type, frosted panels)
- **MediaPipe Hand Landmarker**: VIDEO mode on a background worker (latest-frame queue)
- **PyObjC Quartz / AppKit**: cursor warp, mouse events, Spaces (Ctrl+Arrow)

## Project layout

```text
src/
  main.py                 # loop: capture → track → decide → dispatch → HUD
  config.py               # all tunables
  camera.py               # webcam frames
  hand_tracker.py         # MediaPipe adapter (async VIDEO worker)
  hand_landmarks.py       # orientation-invariant finger geometry
  landmark_filter.py      # One Euro tip filter + active region
  pose_classifier.py      # pointer hand: peace vs point
  scroll_intent_engine.py # three-finger scroll intent
  gesture_engine.py       # click hand: pinch / palm families
  interaction_engine.py   # interaction state → commands
  action_dispatcher.py    # Quartz / AppKit I/O
  hud_renderer.py         # Spatial Control overlay
tests/
  test_gesture_arbitration.py
models/hand_landmarker.task
docs/architecture.md
CHANGELOG.md
```

Pipeline and arbitration details: [docs/architecture.md](docs/architecture.md).

## License

Personal / public learning project unless otherwise noted.
