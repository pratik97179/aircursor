# AirCursor

Hands-free macOS cursor control using a laptop webcam and MediaPipe hand tracking.

AirCursor is built in public. **v0.16.1**: Spatial Control HUD, palm/pinch/fist
arbitration, and background hand inference so the preview stays responsive.

## What works today

1. Detect up to two hands from the built-in webcam.
2. **Pointer hand** (Right) — index fingertip moves the cursor; peace toggles **Cursor Mode**; **index + middle + ring** hold then pull scrolls.
3. **Click hand** (Left) — **thumb + index pinch** (index extended, other fingers curled) to click; hold + move to drag.
4. **Click hand** — **thumb + middle pinch** for right-click.
5. **Click hand** — **open palm hold, then swipe left/right** to switch macOS Spaces (won't collide with click/fist).
6. Preview HUD with gesture feed (last 10 actions), glass chrome, and on-hand cues.
7. Swap roles in `src/config.py` if needed.

## Requirements

- macOS (tested target: Apple Silicon, built-in FaceTime camera)
- Python 3.14+
- [uv](https://github.com/astral-sh/uv)
- **Accessibility** permission for the terminal/IDE that runs AirCursor  
  (System Settings → Privacy & Security → Accessibility), otherwise cursor move and click will fail.

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

Keys in the preview window:

- `q` — quit
- `h` — toggle HUD chrome
- `d` — toggle landmark / geometry debug

## Tech stack

- **Python** + **uv**
- **OpenCV** — webcam capture
- **Pillow** — Spatial Control HUD (SF Pro type, frosted panels)
- **MediaPipe Hand Landmarker** — VIDEO mode on a background worker (latest-frame queue)
- **PyObjC Quartz / AppKit** — cursor warp and mouse / Spaces input

## Project layout

```text
src/
  camera.py
  hand_tracker.py
  hand_landmarks.py
  landmark_filter.py
  pose_classifier.py
  gesture_engine.py
  scroll_intent_engine.py
  interaction_engine.py
  action_dispatcher.py
  hud_renderer.py
  config.py
  main.py
tests/
  test_gesture_arbitration.py
models/hand_landmarker.task
docs/architecture.md
CHANGELOG.md
```

See [docs/architecture.md](docs/architecture.md) for the pipeline, gesture arbitration, and module responsibilities.

## License

Personal / public learning project unless otherwise noted.
