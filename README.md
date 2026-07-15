# AirCursor

Hands-free macOS cursor control using a laptop webcam and MediaPipe hand tracking.

AirCursor is built in public. v0.9 adds pinch-hold drag.

## What works today

1. Detect up to two hands from the built-in webcam.
2. **Pointer hand** (Right) — index fingertip moves the cursor; peace toggles **Cursor Mode**.
3. **Click hand** (Left) — **pinch** briefly to click; **hold pinch + move pointer** to drag.
4. **Click hand** — **two-finger swipe** (index + middle) to scroll.
5. Swap roles in `src/config.py` if needed.

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

Press `q` in the preview window to quit.

## Tech stack

- **Python** + **uv**
- **OpenCV** — webcam capture and HUD
- **MediaPipe Hand Landmarker** — VIDEO mode, CPU, single hand
- **PyObjC Quartz / AppKit** — cursor warp and mouse clicks

## Project layout

```text
src/
  camera.py
  hand_tracker.py
  landmark_filter.py
  pose_classifier.py
  gesture_engine.py
  interaction_engine.py
  action_dispatcher.py
  config.py
  main.py
models/hand_landmarker.task
docs/architecture.md
```

See [docs/architecture.md](docs/architecture.md) for the pipeline and module responsibilities.

## License

Personal / public learning project unless otherwise noted.
