"""Scroll controller — index finger scrolls up, index+middle scrolls down."""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import pyautogui

from apps.hci.config import HCIConfig
from apps.hci.controllers.base import BaseController
from core.landmark_utils import LandmarkUtils

logger = logging.getLogger(__name__)


class ScrollController(BaseController):
    """One finger (index) → scroll up. Two fingers (index+middle) → scroll down."""

    def __init__(self) -> None:
        super().__init__(
            name="Scroll",
            cooldown_ms=HCIConfig.SCROLL_COOLDOWN,
            smoothing_window=HCIConfig.TEMPORAL_SMOOTHING_WINDOW,
            smoothing_threshold=HCIConfig.TEMPORAL_SMOOTHING_THRESHOLD,
        )
        self._scroll_start_time: Optional[float] = None
        self._prev_palm: Optional[Tuple[float, float]] = None

    def detect(
        self,
        landmarks: List[Tuple[float, float, float]],
        handedness: str,
        **kwargs: Any,
    ) -> Optional[str]:
        states = LandmarkUtils.get_all_finger_states(
            landmarks, handedness, HCIConfig.FINGER_EXTENSION_THRESHOLD
        )

        index_only = (
            states["index"]
            and not states["thumb"]
            and not states["middle"]
            and not states["ring"]
            and not states["pinky"]
        )

        two_fingers = (
            states["index"]
            and states["middle"]
            and not states["thumb"]
            and not states["ring"]
            and not states["pinky"]
        )

        if index_only:
            return "scroll_up"
        if two_fingers:
            return "scroll_down"
        return None

    def execute(self, gesture: str, **kwargs: Any) -> Optional[Dict[str, Any]]:
        now = time.time()
        landmarks = kwargs.get("landmarks")
        amount = HCIConfig.SCROLL_AMOUNT

        # Velocity-based scroll scaling
        if HCIConfig.SCROLL_VELOCITY_SCALE and landmarks:
            palm = LandmarkUtils.palm_center(landmarks)
            if self._prev_palm:
                dt = kwargs.get("dt", 1.0 / 30.0)
                _, vy = LandmarkUtils.hand_velocity(palm, self._prev_palm, dt)
                speed = abs(vy)
                # Scale amount based on vertical speed
                scale = min(speed / 0.5, 1.0)
                amount = int(
                    HCIConfig.SCROLL_MIN_AMOUNT
                    + scale * (HCIConfig.SCROLL_MAX_AMOUNT - HCIConfig.SCROLL_MIN_AMOUNT)
                )
            self._prev_palm = palm

        # Scroll acceleration for sustained gesture
        if self._scroll_start_time is None:
            self._scroll_start_time = now
        elapsed = now - self._scroll_start_time
        if elapsed > HCIConfig.SCROLL_ACCELERATION_TIME:
            amount = int(amount * HCIConfig.SCROLL_ACCELERATION_FACTOR)

        if gesture == "scroll_up":
            pyautogui.scroll(amount, _pause=False)
        elif gesture == "scroll_down":
            pyautogui.scroll(-amount, _pause=False)

        return {
            "controller": self.name,
            "action": gesture,
            "amount": amount,
        }

    def process(
        self,
        landmarks: List[Tuple[float, float, float]],
        handedness: str,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        """Override to reset acceleration when gesture stops."""
        result = super().process(landmarks, handedness, **kwargs)
        # Reset acceleration timer when no scroll gesture detected
        raw = self.detect(landmarks, handedness, **kwargs)
        if raw is None:
            self._scroll_start_time = None
            self._prev_palm = None
        return result

    def reset(self) -> None:
        super().reset()
        self._scroll_start_time = None
        self._prev_palm = None
