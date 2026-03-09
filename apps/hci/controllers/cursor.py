"""Cursor controller — open hand moves cursor, pinch clicks/drags."""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import pyautogui

from apps.hci.config import HCIConfig
from apps.hci.controllers.base import BaseController
from core.coordinate_mapper import ScreenMapper
from core.landmark_utils import LandmarkUtils
from core.smoothing import AdaptiveCoordinateSmoother, CoordinateSmoother

logger = logging.getLogger(__name__)

# Disable pyautogui's built-in pause for responsiveness
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = True  # Move mouse to corner to abort


class CursorController(BaseController):
    """Open hand → cursor movement. Pinch → click/double-click/drag."""

    def __init__(self) -> None:
        super().__init__(
            name="Cursor",
            cooldown_ms=HCIConfig.CLICK_COOLDOWN,
            smoothing_window=1,  # No temporal smoothing for cursor (needs responsiveness)
            smoothing_threshold=1,
        )
        screen_w, screen_h = pyautogui.size()
        self._screen_w = screen_w
        self._screen_h = screen_h

        # Coordinate mapper
        self._mapper = ScreenMapper(
            screen_w=screen_w,
            screen_h=screen_h,
            margin_center=HCIConfig.MARGIN_CENTER,
            margin_edge=HCIConfig.MARGIN_EDGE,
            blend_zone=HCIConfig.MARGIN_BLEND_ZONE,
            dead_zone=HCIConfig.CURSOR_DEAD_ZONE,
            flip_x=HCIConfig.FLIP_X,
        )

        # Smoother
        if HCIConfig.ADAPTIVE_SMOOTHING:
            self._smoother = AdaptiveCoordinateSmoother(
                alpha_slow=HCIConfig.ADAPTIVE_ALPHA_SLOW,
                alpha_fast=HCIConfig.ADAPTIVE_ALPHA_FAST,
                velocity_threshold=HCIConfig.ADAPTIVE_VELOCITY_THRESHOLD,
            )
        else:
            self._smoother = CoordinateSmoother(alpha=HCIConfig.CURSOR_SMOOTHING_ALPHA)

        # Pinch state (hysteresis)
        self._pinch_engaged = False
        self._pinch_start_time: Optional[float] = None
        self._last_click_time: float = 0.0
        self._dragging = False

    def detect(
        self,
        landmarks: List[Tuple[float, float, float]],
        handedness: str,
        **kwargs: Any,
    ) -> Optional[str]:
        """Detect cursor movement and pinch gestures."""
        states = LandmarkUtils.get_all_finger_states(
            landmarks, handedness, HCIConfig.FINGER_EXTENSION_THRESHOLD
        )

        # Open hand check: all 5 fingers extended
        all_extended = all(states.values())

        # Pinch distance
        pinch_dist = LandmarkUtils.pinch_distance(landmarks)

        # Pinch hysteresis
        if not self._pinch_engaged:
            if pinch_dist < HCIConfig.PINCH_ENGAGE_THRESHOLD:
                self._pinch_engaged = True
                self._pinch_start_time = time.time()
                return "pinch_start"
        else:
            if pinch_dist > HCIConfig.PINCH_DISENGAGE_THRESHOLD:
                self._pinch_engaged = False
                was_dragging = self._dragging
                self._dragging = False
                self._pinch_start_time = None
                if was_dragging:
                    return "drag_end"
                return "pinch_release"
            # Check for drag (pinch held long enough)
            if (
                self._pinch_start_time
                and not self._dragging
                and (time.time() - self._pinch_start_time) >= HCIConfig.DRAG_HOLD_TIME
            ):
                self._dragging = True
                return "drag_start"

        if all_extended or self._dragging:
            return "move"

        return None

    def execute(self, gesture: str, **kwargs: Any) -> Optional[Dict[str, Any]]:
        """Execute cursor/click/drag actions."""
        landmarks = kwargs.get("landmarks")
        result: Dict[str, Any] = {"controller": self.name, "action": gesture}

        if gesture == "move" and landmarks:
            # Use index fingertip for cursor position
            idx_tip = landmarks[LandmarkUtils.INDEX_TIP]
            raw_x, raw_y = self._mapper.map_to_screen(idx_tip[0], idx_tip[1])
            sx, sy = self._smoother.update(float(raw_x), float(raw_y))
            try:
                pyautogui.moveTo(int(sx), int(sy), _pause=False)
            except pyautogui.FailSafeException:
                logger.warning("[Cursor] Failsafe triggered — mouse in corner")
            result["position"] = (int(sx), int(sy))

        elif gesture == "pinch_start":
            # Ignored — actual click happens on release for clean click vs drag
            result["info"] = "pinch_engaged"

        elif gesture == "pinch_release":
            now = time.time()
            if now - self._last_click_time < HCIConfig.DOUBLE_CLICK_WINDOW:
                pyautogui.doubleClick(_pause=False)
                result["action"] = "double_click"
                self._last_click_time = 0.0
            else:
                pyautogui.click(_pause=False)
                result["action"] = "click"
                self._last_click_time = now

        elif gesture == "drag_start":
            pyautogui.mouseDown(_pause=False)
            result["info"] = "drag_started"

        elif gesture == "drag_end":
            pyautogui.mouseUp(_pause=False)
            result["info"] = "drag_released"

        return result

    def process(
        self,
        landmarks: List[Tuple[float, float, float]],
        handedness: str,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        """Override base process — cursor needs custom flow (no temporal smoothing)."""
        if not self.enabled:
            return None

        gesture = self.detect(landmarks, handedness, **kwargs)
        if gesture is None:
            return None

        # Move doesn't need cooldown
        if gesture == "move":
            return self.execute(gesture, landmarks=landmarks)

        # Click/drag actions go through cooldown
        if gesture in ("pinch_start",):
            return self.execute(gesture, landmarks=landmarks)

        if not self.can_trigger():
            return None

        self._record_trigger()
        return self.execute(gesture, landmarks=landmarks)

    def reset(self) -> None:
        super().reset()
        self._pinch_engaged = False
        self._pinch_start_time = None
        self._last_click_time = 0.0
        self._dragging = False
        self._smoother.reset()
        self._mapper.reset()
