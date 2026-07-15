# AirCursor Architecture (v0.8)

## Pipeline (implemented)

```text
Camera
  → HandTracker (up to 2 hands)
  → LandmarkFilter (pointer hand tip)
  → PoseClassifier (pointer hand)
  → GestureEngine (click hand: pinch + two-finger scroll)
  → InteractionEngine
  → ActionDispatcher
  → macOS
```

`main` wires the loop, draws the HUD, and applies commands from `InteractionEngine`.

---

## Two-hand roles

| Role | Default | Responsibility |
|------|---------|----------------|
| Pointer | `Right` | Peace toggle, index-tip cursor move |
| Click / Navigate | `Left` | Pinch → click; index+middle swipe → scroll |

`SWAP_HANDEDNESS_FOR_MIRROR` keeps labels matched to the mirrored preview.

---

## Responsibilities

### Camera
- Open the built-in webcam (AVFoundation), mirror frames
- Single-frame buffer

### HandTracker
- MediaPipe VIDEO / CPU, up to two hands, optional downscaled inference
- Resolve Left/Right hands; return tip + landmarks

### LandmarkFilter
- One Euro on pointer tip; active-region `tip_valid`

### PoseClassifier
- Pointer hand: `NONE`, `POINT`, `SYSTEM` (peace)

### GestureEngine
- Click hand pinch edges: `PINCH_DOWN` / `PINCH_UP`
- Two-finger pose → scroll point (index + middle tip midpoint)
- Pinch wins over scroll

### InteractionEngine
- Pointing mode + SYSTEM hold
- Commands: `SetCursor`, `Click`, `Scroll` (natural trackpad mapping)

### ActionDispatcher
- Cursor warp + throttled mouse-move events
- Left click; pixel scroll wheel (vertical + horizontal)

---

## Next

- Drag (`MANIPULATE`)
- Multi-monitor clamp
- Automated tests and CI
