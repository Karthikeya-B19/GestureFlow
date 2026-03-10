"""Gesture classifier — priority-based routing to controllers.

Implements:
- Priority-ordered gesture detection (fist > rock_on > thumbs > fingers > open_hand)
- Gesture transition buffer (2 IDLE frames between different gestures)
- Frame skipping when gesture is stable/idle
- Confidence gating (reject low-confidence detections)
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from apps.hci.config import HCIConfig
from apps.hci.controllers.brightness import BrightnessController
from apps.hci.controllers.cursor import CursorController
from apps.hci.controllers.media import MediaController
from apps.hci.controllers.scroll import ScrollController
from apps.hci.controllers.tab_switch import TabSwitchController
from apps.hci.controllers.volume import VolumeController
from core.landmark_utils import LandmarkUtils

logger = logging.getLogger(__name__)


class GestureClassifier:
    """Routes detected gestures to the appropriate controller.

    Priority order (highest first):
      1. Fist        → TabSwitch
      2. Rock-on     → Volume
      3. Thumbs up   → Media (play/pause)
      4. Thumbs down → Media (mute)
      5. 3 fingers   → Brightness up
      6. 4 fingers   → Brightness down
      7. 1 finger    → Scroll up
      8. 2 fingers   → Scroll down
      9. Open hand   → Cursor
    """

    def __init__(self) -> None:
        self.cursor = CursorController()
        self.scroll = ScrollController()
        self.volume = VolumeController()
        self.media = MediaController()
        self.tab_switch = TabSwitchController()
        self.brightness = BrightnessController()

        self._controllers = {
            "cursor": self.cursor,
            "scroll": self.scroll,
            "volume": self.volume,
            "media": self.media,
            "tab_switch": self.tab_switch,
            "brightness": self.brightness,
        }

        # Transition buffer state
        self._last_gesture: Optional[str] = None
        self._idle_frames: int = 0
        self._transition_locked = False

        # Frame skipping state
        self._same_gesture_count: int = 0
        self._skip_next: bool = False

    def classify(
        self,
        landmarks: List[Tuple[float, float, float]],
        handedness: str,
        confidence: float = 1.0,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        """Classify gesture and route to controller.

        Args:
            landmarks: 21 MediaPipe hand landmarks.
            handedness: "Right" or "Left".
            confidence: MediaPipe detection confidence.
            **kwargs: Extra context (dt, prev_landmarks, etc.)

        Returns:
            Action metadata dict from the triggered controller, or None.
        """
        # Confidence gating
        if confidence < HCIConfig.LOW_CONFIDENCE_THRESHOLD:
            logger.debug("Low confidence (%.2f) — skipping", confidence)
            return None

        # Frame skipping
        if self._should_skip_frame():
            return None

        # Classify gesture by priority
        gesture = self._identify_gesture(landmarks, handedness)

        # Transition buffer
        if not self._check_transition(gesture):
            return None

        # Route to controller
        return self._dispatch(gesture, landmarks, handedness, **kwargs)

    def _identify_gesture(
        self,
        landmarks: List[Tuple[float, float, float]],
        handedness: str,
    ) -> str:
        """Identify the highest-priority gesture present."""
        threshold = HCIConfig.FINGER_EXTENSION_THRESHOLD

        # 1. Fist (all curled)
        if LandmarkUtils.is_fist(landmarks, handedness, threshold):
            return "fist"

        # 2. Rock-on (index + pinky extended) — volume
        if LandmarkUtils.is_rock_on(landmarks, handedness, threshold):
            return "rock_on"

        # 3. Thumbs up
        if LandmarkUtils.is_thumbs_up(landmarks, handedness, threshold):
            return "thumbs_up"

        # 4. Thumbs down
        if LandmarkUtils.is_thumbs_down(landmarks, handedness, threshold):
            return "thumbs_down"

        # 5-8. Count-based gestures
        states = LandmarkUtils.get_all_finger_states(landmarks, handedness, threshold)
        non_thumb = [states["index"], states["middle"], states["ring"], states["pinky"]]
        count = sum(non_thumb)

        # Thumb + pinky out (others curled) — brightness down
        if (states["thumb"] and states["pinky"]
                and not states["index"] and not states["middle"] and not states["ring"]):
            return "thumb_pinky"

        if not states["thumb"]:
            if count == 3 and states["index"] and states["middle"] and states["ring"]:
                return "three_fingers"
            if count == 4:
                return "four_fingers"
            if count == 1 and states["index"]:
                return "one_finger"
            if count == 2 and states["index"] and states["middle"]:
                return "two_fingers"

        # Open hand (all 5)
        if all(states.values()):
            return "open_hand"

        return "idle"

    def _check_transition(self, gesture: str) -> bool:
        """Enforce transition buffer between different gestures.

        Requires GESTURE_TRANSITION_BUFFER frames of IDLE between
        switching from one gesture to another.
        """
        if gesture == "idle":
            self._idle_frames += 1
            if self._idle_frames >= HCIConfig.GESTURE_TRANSITION_BUFFER:
                self._transition_locked = False
            self._last_gesture = "idle"
            return False

        if gesture == self._last_gesture:
            self._idle_frames = 0
            return True

        # Different gesture from last
        if self._transition_locked:
            return False

        # First time seeing a new gesture — require transition
        if self._last_gesture is not None and self._last_gesture != "idle":
            self._transition_locked = True
            self._idle_frames = 0
            return False

        self._last_gesture = gesture
        self._idle_frames = 0
        return True

    def _should_skip_frame(self) -> bool:
        """Frame skipping: skip every other frame when gesture is stable/idle."""
        if not HCIConfig.FRAME_SKIP_ENABLED:
            return False

        if self._skip_next:
            self._skip_next = False
            return True

        if self._same_gesture_count >= HCIConfig.FRAME_SKIP_STABLE_COUNT:
            if self._last_gesture in ("idle", "open_hand"):
                self._skip_next = True

        return False

    def _dispatch(
        self,
        gesture: str,
        landmarks: List[Tuple[float, float, float]],
        handedness: str,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        """Dispatch to the appropriate controller."""
        # Track gesture stability for frame skipping
        if gesture == self._last_gesture:
            self._same_gesture_count += 1
        else:
            self._same_gesture_count = 0
        self._last_gesture = gesture

        if gesture == "fist":
            return self.tab_switch.process(landmarks, handedness, **kwargs)
        if gesture == "rock_on":
            return self.volume.process(landmarks, handedness, **kwargs)
        if gesture == "thumbs_up":
            return self.media.process(landmarks, handedness, **kwargs)
        if gesture == "thumbs_down":
            return self.media.process(landmarks, handedness, **kwargs)
        if gesture == "three_fingers":
            return self.brightness.process(landmarks, handedness, **kwargs)
        if gesture == "thumb_pinky":
            return self.brightness.process(landmarks, handedness, **kwargs)
        if gesture == "four_fingers":
            return self.brightness.process(landmarks, handedness, **kwargs)
        if gesture == "one_finger":
            return self.scroll.process(landmarks, handedness, **kwargs)
        if gesture == "two_fingers":
            return self.scroll.process(landmarks, handedness, **kwargs)
        if gesture == "open_hand":
            return self.cursor.process(landmarks, handedness, **kwargs)

        return None

    def enable_all(self) -> None:
        for ctrl in self._controllers.values():
            ctrl.enable()

    def disable_all(self) -> None:
        for ctrl in self._controllers.values():
            ctrl.disable()

    def reset(self) -> None:
        for ctrl in self._controllers.values():
            ctrl.reset()
        self._last_gesture = None
        self._idle_frames = 0
        self._transition_locked = False
        self._same_gesture_count = 0
        self._skip_next = False
