"""
Application configuration.

All tunable values for AirCursor live here.
"""

# Camera

CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720

# Pose / interaction

ACTIVATION_DELAY = 0.3  # seconds to hold SYSTEM (peace) before toggle

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
