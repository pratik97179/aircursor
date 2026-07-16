"""
Application configuration.

All tunable values for AirCursor live here.
"""

# Camera

CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720

# Run MediaPipe on a downscaled frame (landmarks are normalized, so tip
# coords stay valid). Biggest CPU win after capture itself.
INFERENCE_WIDTH = 640
INFERENCE_HEIGHT = 360

# Debug HUD
SHOW_LANDMARKS = False  # full 21-point skeletons are expensive; tip marker stays on

# How often to emit CG mouse-moved events while warping (Zoom/Electron hover).
# 0 = every move frame (costly); 30 ≈ every 33ms.
MOUSE_MOVE_EVENT_HZ = 30

# Pose / interaction

ACTIVATION_DELAY = 0.3  # seconds to hold SYSTEM (peace) before toggle

# Two-hand roles from the user's perspective ("Left" / "Right").
# Right hand points; left hand pinches to click.
# Labels are corrected for the mirrored webcam preview.

POINTER_HANDEDNESS = "Right"
CLICK_HANDEDNESS = "Left"
# Camera frames are mirrored; MediaPipe handedness is swapped to match the user.
SWAP_HANDEDNESS_FOR_MIRROR = True

NUM_HANDS = 2

# Pinch / click on the click hand only (thumb tip ↔ index tip / hand scale)

PINCH_ENTER = 0.35
PINCH_EXIT = 0.42  # closer to enter so brief pinches release cleanly
CLICK_DEBOUNCE = 0.25  # seconds between click/drag arms

# Click vs drag (pinch is pending until one of these fires)
# Release before promote → single click. Move or hold → mouse-down (drag).
DRAG_SLOP = 0.014  # normalized pointer travel to promote to drag
DRAG_ARM_HOLD = 0.35  # seconds held still before arming drag

# Pointer-hand three-finger scroll (index + middle + ring up, dwell then rubber-band pull).
# Positive pull down (increasing y) → natural content scroll down when SCROLL_NATURAL.

SCROLL_INTENT_DWELL = 0.2  # seconds three fingers must be held before scroll arms
SCROLL_RUBBER_GAIN = 2200.0
SCROLL_RUBBER_EXPONENT = 1.35
SCROLL_RUBBER_DEAD_ZONE = 2.0  # min incremental wheel units per frame
SCROLL_REANCHOR_THRESHOLD = 0.008  # normalized; hand near anchor resets strength
SCROLL_MAX_DELTA_PER_FRAME = 400  # cap wheel units per frame
SCROLL_NATURAL = True  # True = MacBook-like (fingers push content)

# Five-finger open-hand horizontal swipe → switch macOS Spaces (Ctrl+Arrow).
SPACE_SWIPE_THRESHOLD = 0.06  # normalized palm travel to fire one switch
SPACE_SWIPE_COOLDOWN = 0.55  # seconds between space switches
SPACE_SWIPE_INVERT = False  # True swaps left/right mapping
SPACE_PALM_GRACE = 0.5  # keep armed briefly if open-palm flickers mid-swipe
SPACE_KEY_HOLD = 0.04  # seconds between arrow down/up (matches a real tap)

# Cursor gain (screen pixels per normalized hand delta).
# Slow motion uses MIN for icon aiming; fast motion ramps toward MAX.

CURSOR_GAIN_MIN = 1.0
CURSOR_GAIN_MAX = 2.4
CURSOR_GAIN_SPEED_REF = 0.012  # tip speed (norm units / sec) at which gain nears MAX

# One Euro filter on the tip (signal smoothing)

ONE_EURO_MIN_CUTOFF = 1.2
ONE_EURO_BETA = 0.007
ONE_EURO_D_CUTOFF = 1.0

TIP_LOSS_GRACE_FRAMES = 4  # tolerate brief MediaPipe dropouts

# Active tracking region (normalized frame coords)

ACTIVE_REGION_LEFT = 0.05
ACTIVE_REGION_RIGHT = 0.95
ACTIVE_REGION_TOP = 0.05
ACTIVE_REGION_BOTTOM = 0.95
