# AirCursor Architecture (v0.12)

## Pipeline (implemented)

```text
Camera
  → HandTracker (up to 2 hands)
  → LandmarkFilter (pointer hand tip)
  → PoseClassifier (pointer hand: peace vs point)
  → ScrollIntentEngine (pointer hand: three-finger scroll)
  → GestureEngine (click hand: pinch + palm)
  → InteractionEngine
  → ActionDispatcher
  → macOS
```

---

## Two-hand roles

| Role | Default | Responsibility |
|------|---------|----------------|
| Pointer | `Right` | Peace toggle, index-tip cursor, three-finger scroll |
| Click / Navigate | `Left` | Thumb+index click/drag; thumb+middle right-click; open palm → Spaces |

---

## Scroll (pointer hand)

1. Hold **index + middle + ring** up for `SCROLL_INTENT_DWELL` (0.2s).
2. Pull hand up/down from anchor — rubber-band incremental scroll.
3. Cursor movement suppressed while scroll intent is active.
4. Peace requires **ring down**; scroll requires **ring up**.

---

## Next

- Multi-monitor clamp
- Automated tests and CI
