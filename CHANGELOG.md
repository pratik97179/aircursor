# Changelog

All notable changes to AirCursor are documented in this file.

## [0.5.0]

### Added

- Added gesture-based cursor activation using.
- Added relative cursor movement to eliminate cursor teleportation.
- Switched cursor control back to the index fingertip.
- Added gesture activation timing using a monotonic clock.

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
