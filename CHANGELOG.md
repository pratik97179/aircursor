# Changelog

All notable changes to AirCursor are documented in this file.

## [0.16.1]

### Changed

- Removed the bottom-left current-gesture card; the right pointer card remains.
- Gesture feed is now newest-at-top: entries slide/fade in at the top, older
  entries move downward, and the oldest fades/slides out at the bottom.
- MediaPipe `VIDEO` inference now runs on a background worker with a one-frame
  latest-only queue; stale frames are dropped instead of blocking webcam/UI.

### Performance

- HUD-only rendering benchmarks around 9 ms/frame at 1280×720; the previous
  dominant stall was synchronous 960×540 two-hand MediaPipe inference.

## [0.16.0]

### Added

- Game-style gesture feed on the left, showing the latest 10 recognized
  gestures/actions with newest at the bottom.
- New entries slide/fade in; older rows shift upward and the oldest fades and
  slides out when the feed exceeds 10 entries.

### Changed

- Replaced the temporary center action flash with the persistent gesture feed.
- Feed events include Cursor On/Off, Click, Right Click, Drag, Scroll Armed,
  Palm Armed, and directional Space switches.

## [0.15.4]

### Fixed

- Right-click reliability: no longer cancel mid-gesture when the index finger
  briefly reads extended. Target tip is chosen by distance margin
  (`PINCH_TARGET_MARGIN`) — thumb nearer middle → right-click, nearer index →
  left-click. Ring+pinky must still be curled; fists still never click.

## [0.15.3]

### Fixed

- Closed left-hand fist no longer triggers click/drag/right-click when the
  thumb rests on curled fingertips. Clicks require an explicit pinch pose:
  index extended for left-click, middle extended for right-click; a fist
  cancels an in-flight pinch instead of completing it.

## [0.15.2]

### Changed

- Palm movement HUD now mirrors scroll feedback: dwell progress, an anchored
  rubber-band, and a direction arrow based on actual left/right movement.
- Pre-arm palm feedback uses a symmetric two-way arrow instead of implying
  only one available direction.

## [0.15.1]

### Fixed

- Spaces swipe now tracks **left** as well as right: re-arm after each switch
  so the opposite direction can fire without closing the palm, and keep
  tracking via `palm_candidate` mid-swipe when the thumb flickers.

## [0.15.0]

### Fixed

- Open-palm Spaces no longer collides with click: palm and pinch are mutually
  exclusive gesture families. Opening/closing the palm cancels pending pinches
  instead of emitting a click; a short lockout blocks phantom tip contact.

### Changed

- Pinch starts only in the pinch family (ring + pinky curled).
- Spaces requires a stable open-palm dwell (`SPACE_PALM_DWELL`) before arming,
  then a horizontal-dominant swipe (`SPACE_SWIPE_AXIS_RATIO`).
- HUD distinguishes palm hold vs palm armed; pinch connectors hidden during palm.

### Added

- `PINCH_CANCEL` / `RIGHT_PINCH_CANCEL` signals; `palm_candidate` on click signal.
- Regression tests in `tests/test_gesture_arbitration.py`.

## [0.14.0]

### Changed

- **HUD visual overhaul**: chrome is now composited with Pillow for real
  anti-aliased **SF Pro** typography and true **frosted-glass** panels
  (Gaussian blur-behind + soft drop shadows + hairline borders + accent rails).
- Top bar redesigned into two floating glass islands (brand/tracking + mode).
- Hand cards now show eyebrow, live status, and contextual guidance line.
- Center action flash: frosted pill with expanding accent ring and pop-in.
- Modern accent palette (tailwind-style greens/orange/cyan/violet).

### Added

- `pillow` dependency for HUD text and glass rendering.

## [0.13.1]

### Fixed

- Removed full-frame black vignette that crushed camera brightness.

### Changed

- HUD polish: glass panels (local only), corner brackets, glow rings, pulse
  accents, expanding action flash — no dark wash over the live feed.

## [0.13.0]

### Added

- **Spatial Control HUD** (`hud_renderer.py`): translucent top bar, hand role
  cards, gesture-specific overlays, and center action flashes.
- Scroll HUD data: `ScrollIntentSignal.dwell_progress`, `anchor`, `centroid`.
- Keys: `H` toggles HUD chrome; `D` toggles landmark/geometry debug.

### Changed

- Webcam preview no longer shows always-on geometry fingertip dots; debug
  overlays are opt-in via `HUD_SHOW_DEBUG` / `D`.

## [0.12.2]

### Fixed

- Finger extended/curled is now hand-relative (MCP→PIP→TIP), not screen-Y —
  tilted hands no longer false-trigger peace / scroll / open palm.
- MediaPipe confidence raised; inference bumped to 960×540; handedness score gate.
- Debug overlay shows geometry-true extended fingertips; full skeleton via
  `SHOW_LANDMARKS`.

## [0.12.1]

### Changed

- Scroll feel polish: faster dwell (0.16s), dwell/armed grace frames, gentler
  rubber curve, lower per-frame cap, smoother centroid filter.
- Peace timer resets when three-finger scroll pose is detected.

## [0.12.0]

### Changed

- Scroll moved to **right hand**: hold index + middle + ring up (0.2s), then pull
  vertically for rubber-band scroll. Cursor freezes while scroll intent is active.
- Left hand no longer scrolls (click, right-click, drag, Spaces only).
- Peace vs scroll split: ring down = peace; ring up = scroll intent.

## [0.11.0]

### Added

- Left-hand thumb + middle pinch → atomic right-click.
- HUD `R-CLICK` flash; Quartz right mouse down/up via `RightClick` command.

## [0.10.2]

### Fixed

- Space switch uses fast Quartz HID key events (no AppleScript) with realistic
  key hold timing so Mission Control animation matches Ctrl+Arrow.

## [0.10.1]

### Fixed

- Space swipe: trigger Spaces via System Events (Accessibility), with Quartz
  Control+Fn+Arrow as fallback — Mission Control often ignored bare CGEvents.
- Open-palm detection is more tolerant mid-swipe; brief flicker no longer resets.
- Lower swipe travel threshold; HUD shows `PALM — swipe` while armed.

## [0.10.0]

### Added

- Left-hand five-finger open-palm swipe switches macOS Spaces (Ctrl+Left / Ctrl+Right).
- `SwitchSpace` command and Quartz keyboard shortcuts.
- HUD `SPACE` flash when a desktop switch fires.
- Tunables: `SPACE_SWIPE_THRESHOLD`, `SPACE_SWIPE_COOLDOWN`, `SPACE_SWIPE_INVERT`.

## [0.9.1]

### Fixed

- Quick pinch no longer holds the mouse button; short pinch is an atomic click.
- Drag only arms after pointer travel (`DRAG_SLOP`) or a short hold (`DRAG_ARM_HOLD`).
- Easier pinch release (`PINCH_EXIT` closer to enter).

## [0.9.0]

### Added

- Drag via left-hand pinch hold + right-hand move (`MouseDown` / `MouseUp`).
- Left-mouse-dragged events while the button is held so Finder/apps track drags.
- HUD `DRAG` state while pinched in Cursor Mode.

### Changed

- Short pinch still acts as a click (down then up); hold + move drags.
- Cursor mode off while held forces mouse-up so the button cannot stick.

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
