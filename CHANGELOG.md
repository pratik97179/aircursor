# Changelog

All notable changes to AirCursor are documented in this file.

## [0.6.0]

### Added

- Introduced architecture layers: Camera, LandmarkFilter, PoseClassifier, InteractionEngine, ActionDispatcher.
- PoseClassifier with `NONE`, `POINT`, and `SYSTEM` (peace) families.
- InteractionEngine owns pointing mode, SYSTEM hold timing, and relative cursor math.
- LandmarkFilter tip EMA, dead zone, and active-region gating.
- ActionDispatcher Quartz cursor get/set with screen clamping.
- Project entrypoint (`uv run aircursor`) and config-backed tunables.

### Changed

- HandTracker uses MediaPipe VIDEO mode with CPU delegate and a project-root model path.
- Camera capture uses AVFoundation at 1280×720 when available.
- Docs and package metadata aligned with the running pipeline.

### Removed

- GestureEngine and CursorController (responsibilities split into PoseClassifier, InteractionEngine, and ActionDispatcher).

## [0.5.0]

### Added

- Gesture-based cursor activation using a peace-sign hold.
- Relative cursor movement to eliminate cursor teleportation.
- Switched cursor control back to the index fingertip.
- Gesture activation timing using a monotonic clock.

### Changed

- Refactored CursorController to own its enabled state.
- Simplified main application loop by delegating cursor state management.
- Introduced a configurable control point abstraction in HandTracker.

## [0.4.0]

### Added

- Introduced a dedicated cursor controller.
- Added an active tracking region for cursor control.
- Mapped the active region to the full display.
- Applied cursor smoothing.

## [0.3.0]

### Added

- Extracted the index fingertip landmark.
- Highlighted the index fingertip on the video feed.
- Displayed live fingertip coordinates.

## [0.2.0]

### Added

- Integrated MediaPipe Tasks API.
- Added real-time hand detection.
- Rendered 21 hand landmarks on the webcam feed.

## [0.1.0]

### Added

- Initialized the AirCursor project.
- Configured the Python development environment with `uv`.
- Added project dependencies.
- Implemented the initial OpenCV webcam pipeline.
- Displayed the live webcam feed.
- Configured Git and GitHub for version control.
