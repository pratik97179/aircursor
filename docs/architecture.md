# AirCursor Architecture (v0.11)

## Pipeline (implemented)

```text
Camera
  → HandTracker (up to 2 hands)
  → LandmarkFilter (pointer hand tip)
  → PoseClassifier (pointer hand)
  → GestureEngine (click hand: pinches + scroll + palm)
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
| Click / Navigate | `Left` | Thumb+index click/drag; thumb+middle right-click; two-finger scroll; open palm → Spaces |


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
- Thumb+index pinch edges: `PINCH_DOWN` / `PINCH_UP`
- Thumb+middle pinch edges: `RIGHT_PINCH_DOWN` / `RIGHT_PINCH_UP`
- Two-finger pose → scroll point (index + middle tip midpoint)
- Open palm → palm point for Spaces swipe
- Priority: index pinch > middle pinch > open palm > scroll

### InteractionEngine
- Pointing mode + SYSTEM hold
- Commands: `SetCursor`, `Click`, `RightClick`, `MouseDown`, `MouseUp`, `Scroll`, `SwitchSpace`
- Pending index pinch: quick release → `Click`; hold/move → drag
- Middle pinch release → `RightClick` (atomic)
- Open-palm horizontal swipe → Space switch (palm grace mid-swipe; HUD `PALM — swipe`)

### ActionDispatcher
- Cursor warp + throttled mouse-move events
- Left/right click; pixel scroll wheel; Quartz Ctrl+Arrow Space switching

---

## Next

- Multi-monitor clamp
- Automated tests and CI
