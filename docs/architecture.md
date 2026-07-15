# AirCursor Architecture v1

## Pipeline

Camera
↓
HandTracker
↓
PoseClassifier
↓
InteractionEngine
↓
GestureEngine
↓
ActionDispatcher
↓
macOS

---

## Responsibilities

### HandTracker
- Detect hands
- Return landmarks
- No state

### PoseClassifier
- Classify interaction family
- POINT
- SELECT
- MANIPULATE
- NAVIGATE
- SYSTEM
- No OS actions

### InteractionEngine
- Owns the global state
- Resolves conflicts
- Decides current interaction

### GestureEngine
- Detects gestures inside the current interaction
- Stateless

### ActionDispatcher
- Converts interactions into macOS events
