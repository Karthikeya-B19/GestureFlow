"""Brightness controller — 3 fingers → up, 4 fingers → down."""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from apps.hci.config import HCIConfig
from apps.hci.controllers.base import BaseController
from core.landmark_utils import LandmarkUtils

logger = logging.getLogger(__name__)


def _get_brightness() -> Optional[int]:
    try:
        import screen_brightness_control as sbc

        level = sbc.get_brightness()
        if isinstance(level, list):
            return level[0]
        return level
    except Exception as e:
        logger.warning("Brightness read failed: %s", e)
        return None


def _set_brightness(value: int) -> bool:
    try:
        import screen_brightness_control as sbc

        sbc.set_brightness(value)
        return True
    except Exception as e:
        logger.warning("Brightness set failed: %s", e)
        return False


class BrightnessController(BaseController):
    """3 fingers (index+middle+ring) → brightness up. 4 fingers → brightness down."""

    def __init__(self) -> None:
        super().__init__(
            name="Brightness",
            cooldown_ms=HCIConfig.BRIGHTNESS_COOLDOWN,
            smoothing_window=HCIConfig.TEMPORAL_SMOOTHING_WINDOW,
            smoothing_threshold=HCIConfig.TEMPORAL_SMOOTHING_THRESHOLD,
        )
        self._hold_start_time: Optional[float] = None
        self._last_gesture: Optional[str] = None

        # Check if brightness control works on this display
        if _get_brightness() is None:
            self.enabled = False
            logger.warning("[Brightness] Disabled — display does not support software brightness")

    def detect(
        self,
        landmarks: List[Tuple[float, float, float]],
        handedness: str,
        **kwargs: Any,
    ) -> Optional[str]:
        states = LandmarkUtils.get_all_finger_states(
            landmarks, handedness, HCIConfig.FINGER_EXTENSION_THRESHOLD
        )

        three_fingers = (
            states["index"]
            and states["middle"]
            and states["ring"]
            and not states["thumb"]
            and not states["pinky"]
        )

        four_fingers = (
            states["index"]
            and states["middle"]
            and states["ring"]
            and states["pinky"]
            and not states["thumb"]
        )

        if three_fingers:
            return "brightness_up"
        if four_fingers:
            return "brightness_down"

        # Reset hold timer when gesture changes
        self._hold_start_time = None
        self._last_gesture = None
        return None

    def execute(self, gesture: str, **kwargs: Any) -> Optional[Dict[str, Any]]:
        current = _get_brightness()
        if current is None:
            return None

        # Step scaling — larger step for sustained hold
        now = time.time()
        step = HCIConfig.BRIGHTNESS_SMALL_STEP

        if self._last_gesture == gesture and self._hold_start_time:
            held = now - self._hold_start_time
            if held > HCIConfig.BRIGHTNESS_HOLD_ACCEL_TIME:
                step = HCIConfig.BRIGHTNESS_LARGE_STEP
        else:
            self._hold_start_time = now

        self._last_gesture = gesture

        if gesture == "brightness_up":
            new_val = min(100, current + step)
        else:
            new_val = max(0, current - step)

        if not _set_brightness(new_val):
            return None

        logger.debug("[Brightness] Set to %d%%", new_val)
        return {
            "controller": self.name,
            "action": gesture,
            "brightness": new_val,
        }

    def reset(self) -> None:
        super().reset()
        self._hold_start_time = None
        self._last_gesture = None
