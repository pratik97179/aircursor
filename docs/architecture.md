# AirCursor Architecture (v0.7)

## Pipeline (implemented)

```text
Camera
  → HandTracker (up to 2 hands)
  → LandmarkFilter (pointer hand tip)
  → PoseClassifier (pointer hand)
  → GestureEngine (click hand pinch)
  → InteractionEngine
  → ActionDispatcher
  → macOS
```

`main` wires the loop, draws the HUD, and applies commands returned by `InteractionEngine`.

---

## Two-hand roles

Configured in `config.py` (user's physical hands; mirror-corrected):

| Role | Default | Responsibility |
|------|---------|----------------|
| Pointer | `Right` | Peace toggle (`SYSTEM`), index-tip cursor move |
| Click | `Left` | Pinch → left click |

`SWAP_HANDEDNESS_FOR_MIRROR` keeps Right/Left matching what you see after the mirrored preview.

---

## Responsibilities

### Camera
- Open the built-in webcam (AVFoundation)
- Read mirrored frames
- No computer-vision logic

### HandTracker
- MediaPipe Hand Landmarker (VIDEO mode, CPU, up to two hands)
- Resolve Left/Right by MediaPipe handedness
- Return pointer tip and each hand's landmarks
- No interaction state

### LandmarkFilter
- One Euro smoothing on the **pointer** tip only
- Active-region gate (`tip_valid`)
- Signal state only (not interaction policy)

### PoseClassifier
- Stateless pose from the **pointer** hand
- Release set: `NONE`, `POINT`, `SYSTEM`
- No OS actions, no hold timers

### GestureEngine
- Pinch edge events on the **click** hand: `PINCH_DOWN` / `PINCH_UP`
- Frame-to-frame pinched bit only; no click debounce / mode

### InteractionEngine
- Owns pointing mode and SYSTEM hold/latch
- Incremental cursor motion with speed-based gain; resume re-anchor
- On click-hand `PINCH_DOWN` while pointing: emit `Click` (debounced)
- Pointer motion continues while the other hand pinches
- Returns commands (`SetCursor`, `Click`); never imports Quartz

### ActionDispatcher
- macOS cursor get/set via Quartz
- Left-click via Quartz mouse down/up
- Screen-bound clamp
- No mode or pose policy

---

## Next

- Pose families: `MANIPULATE`, `NAVIGATE`
- Scroll and drag
- Multi-monitor clamp
- Optional Apple Vision backend behind `HandTracker`
- Automated tests and CI
