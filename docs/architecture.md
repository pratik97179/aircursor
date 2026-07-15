# AirCursor Architecture (v0.6)

## Pipeline (implemented)

```text
Camera
  → HandTracker
  → LandmarkFilter
  → PoseClassifier
  → InteractionEngine
  → ActionDispatcher
  → macOS
```

`main` wires the loop, draws the HUD, and applies commands returned by `InteractionEngine`.

---

## Responsibilities

### Camera
- Open the built-in webcam (AVFoundation)
- Read mirrored frames
- No computer-vision logic

### HandTracker
- MediaPipe Hand Landmarker (VIDEO mode, CPU, one hand)
- Return landmarks and index fingertip
- No interaction state

### LandmarkFilter
- Tip One Euro smoothing
- Active-region gate (`tip_valid`)
- Signal state only (not interaction policy)

### PoseClassifier
- Stateless pose family from landmarks
- Release set: `NONE`, `POINT`, `SYSTEM`
- No OS actions, no hold timers

### InteractionEngine
- Owns pointing mode and SYSTEM hold/latch
- Relative cursor anchors and move math
- Returns commands (`SetCursor`); never imports Quartz

### ActionDispatcher
- macOS cursor get/set via Quartz
- Screen-bound clamp
- No mode or pose policy

---

## Next (not in v0.6)

- `GestureEngine` for edge events (e.g. pinch) inside `SELECT`
- Pose families: `SELECT`, `MANIPULATE`, `NAVIGATE`
- Optional Apple Vision backend behind `HandTracker`
- Clutch / re-anchor / velocity gain
- Multi-monitor clamp
- Automated tests and CI
