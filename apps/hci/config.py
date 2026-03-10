"""HCI application configuration — thresholds, cooldowns, feature toggles."""


class HCIConfig:
    """Central configuration for GestureFlow HCI application."""

    # --- Camera ---
    CAMERA_INDEX = 0
    CAMERA_WIDTH = 640
    CAMERA_HEIGHT = 480
    MAX_FPS = 30

    # --- MediaPipe ---
    MODEL_COMPLEXITY = 0  # 0=lite (fast), 1=full (precise)
    MIN_DETECTION_CONFIDENCE = 0.7
    MIN_TRACKING_CONFIDENCE = 0.5
    LOW_CONFIDENCE_THRESHOLD = 0.3  # Reject detections below this

    # --- Cursor ---
    CURSOR_SMOOTHING_ALPHA = 0.5
    CURSOR_DEAD_ZONE = 3  # pixels — suppress movements smaller than this
    ADAPTIVE_SMOOTHING = True
    ADAPTIVE_ALPHA_SLOW = 0.2
    ADAPTIVE_ALPHA_FAST = 0.8
    ADAPTIVE_VELOCITY_THRESHOLD = 50.0
    EDGE_MARGIN_COMPENSATION = True
    MARGIN_CENTER = 0.05
    MARGIN_EDGE = 0.015
    MARGIN_BLEND_ZONE = 0.15
    FLIP_X = True  # Mirror webcam for natural cursor

    # --- Pinch (Click) ---
    PINCH_ENGAGE_THRESHOLD = 0.05  # Pinch distance to START click
    PINCH_DISENGAGE_THRESHOLD = 0.07  # Pinch distance to END click (hysteresis)
    DOUBLE_CLICK_WINDOW = 0.4  # seconds between pinches for double-click
    DRAG_HOLD_TIME = 0.3  # seconds pinch held to enter drag mode
    CLICK_COOLDOWN = 200  # ms

    # --- Scroll ---
    SCROLL_AMOUNT = 3  # lines per scroll event
    SCROLL_COOLDOWN = 150  # ms
    SCROLL_VELOCITY_SCALE = True  # Scale scroll by hand speed
    SCROLL_MIN_AMOUNT = 1
    SCROLL_MAX_AMOUNT = 10
    SCROLL_ACCELERATION_TIME = 1.0  # seconds before accelerating
    SCROLL_ACCELERATION_FACTOR = 2.0

    # --- Volume ---
    VOLUME_COOLDOWN = 300  # ms
    VOLUME_VELOCITY_THRESHOLD = 0.02  # Ignore velocity below this
    VOLUME_SMALL_STEP = 2  # percent
    VOLUME_LARGE_STEP = 10  # percent
    VOLUME_VELOCITY_LARGE = 0.08  # Velocity above = large step
    VOLUME_DEVICE_RETRY_INTERVAL = 30.0  # seconds

    # --- Media ---
    MEDIA_COOLDOWN = 1000  # ms

    # --- Tab Switch ---
    TAB_SWITCH_COOLDOWN = 1500  # ms
    TAB_SWITCH_HOLD_TIME = 0.5  # seconds fist must be held
    TAB_DIRECTION_VELOCITY_THRESHOLD = 0.03  # x-velocity for direction detect

    # --- Brightness ---
    BRIGHTNESS_COOLDOWN = 800  # ms
    BRIGHTNESS_SMALL_STEP = 10  # percent
    BRIGHTNESS_LARGE_STEP = 20  # percent
    BRIGHTNESS_HOLD_ACCEL_TIME = 2.0  # seconds for accelerated step

    # --- Temporal Smoothing ---
    TEMPORAL_SMOOTHING_WINDOW = 5  # frames to buffer
    TEMPORAL_SMOOTHING_THRESHOLD = 3  # min agreement count

    # --- Gesture Classifier ---
    FRAME_SKIP_ENABLED = True
    FRAME_SKIP_STABLE_COUNT = 5  # consecutive stable frames before skipping
    GESTURE_TRANSITION_BUFFER = 1  # frames of IDLE between gesture changes
    GESTURE_PRIORITY_ORDER = [
        "fist",
        "rock_on",
        "thumbs_up",
        "thumbs_down",
        "three_fingers",
        "four_fingers",
        "one_finger",
        "two_fingers",
        "open_hand",
    ]

    # --- Finger Extension ---
    FINGER_EXTENSION_THRESHOLD = 0.005

    # --- Overlay ---
    OVERLAY_OPACITY = 0.85
    OVERLAY_SHOW_FPS = True
    OVERLAY_CLICK_THROUGH = False
    OVERLAY_SHOW_WEBCAM = False

    # --- General ---
    START_MINIMIZED = False
    ENABLE_ALL_GESTURES = True
