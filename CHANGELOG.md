# Changelog

All notable changes to AirCursor are documented in this file.

## [0.8.0]

### Added

- Left-hand two-finger swipe scroll (index + middle), MacBook trackpad-style.
- `Scroll` command and Quartz pixel scroll wheel events (vertical + horizontal).
- HUD `SCROLL` state while two-finger scrolling in Cursor Mode.

### Changed

- GestureEngine reports click-hand pinch and two-finger scroll point together.
- Pinch still wins over scroll when active.

## [0.7.0]

### Added

- Two-hand input: right hand points; left hand pinches to left-click.
- Configurable `POINTER_HANDEDNESS` / `CLICK_HANDEDNESS` with mirror-corrected labels.
- GestureEngine with hysteretic `PINCH_DOWN` / `PINCH_UP` on the click hand only.
- Left-click while Cursor Mode is on (InteractionEngine `Click` + ActionDispatcher Quartz events).
- Click debounce; pointer tip stays independent of the click pinch.
- HUD shows `CLICK` while the click hand is pinched in Cursor Mode.

### Changed

- HandTracker tracks up to two hands, resolves roles in one pass, and can run inference at 640×360.
- PoseClassifier no longer treats pinch as a pointer pose.
- ActionDispatcher caches cursor position, throttles mouse-move events, and dual-taps clicks for Zoom/Electron.
- Camera uses a single-frame buffer; debug skeletons are off by default (`SHOW_LANDMARKS`).
- Architecture docs and README updated for two-hand click and performance tunables.
- Package version set to 0.7.0.

## [0.6.0]

### Added

- Introduced architecture layers: Camera, LandmarkFilter, PoseClassifier, InteractionEngine, ActionDispatcher.
- PoseClassifier with `NONE`, `POINT`, and `SYSTEM` (peace) families.
- InteractionEngine owns pointing mode, SYSTEM hold timing, and cursor motion.
- LandmarkFilter One Euro tip smoothing, active-region gating, and tip-loss grace.
- Speed-based cursor gain and resume re-anchoring.
- ActionDispatcher Quartz cursor get/set with screen clamping.
- Project entrypoint (`uv run aircursor`) and config-backed tunables.

### Changed

- HandTracker uses MediaPipe VIDEO mode with CPU delegate and a resolved model path.
- Camera capture uses AVFoundation at 1280×720 when available.
- Docs and package metadata aligned with the running pipeline.

### Removed

- Earlier GestureEngine / CursorController MVP modules (replaced by PoseClassifier, InteractionEngine, and ActionDispatcher; GestureEngine returns in 0.7 for pinch edges).

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
