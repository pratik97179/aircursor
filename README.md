# AirCursor

Hands-free macOS cursor control using a laptop webcam and MediaPipe hand tracking.

AirCursor is built in public. v0.6 is the first architecture-aligned release: pose classification, interaction state, and OS cursor I/O are separated cleanly.

## What works today

1. Detect a hand from the built-in webcam.
2. Track the index fingertip (smoothed, active-region gated).
3. Hold a **peace sign** (~0.3s) to toggle **Cursor Mode**.
4. Move the macOS cursor with relative fingertip motion.

Clicks, scrolling, and drag are not implemented yet.

## Requirements

- macOS (tested target: Apple Silicon, built-in FaceTime camera)
- Python 3.14+
- [uv](https://github.com/astral-sh/uv)
- **Accessibility** permission for the terminal/IDE that runs AirCursor  
  (System Settings → Privacy & Security → Accessibility), otherwise the cursor will not move.

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
- **PyObjC Quartz / AppKit** — cursor position and warp

## Project layout

```text
src/
  camera.py
  hand_tracker.py
  landmark_filter.py
  pose_classifier.py
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
