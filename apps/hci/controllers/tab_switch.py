"""Tab switch controller — fist hold → Alt+Tab, with direction awareness."""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from pynput.keyboard import Controller as KbController
from pynput.keyboard import Key

from apps.hci.config import HCIConfig
from apps.hci.controllers.base import BaseController
from core.landmark_utils import LandmarkUtils

logger = logging.getLogger(__name__)


class TabSwitchController(BaseController):
    """Fist held 500ms → Alt+Tab. Fist + hand left → Alt+Shift+Tab."""

    def __init__(self) -> None:
        super().__init__(
            name="TabSwitch",
            cooldown_ms=HCIConfig.TAB_SWITCH_COOLDOWN,
            smoothing_window=HCIConfig.TEMPORAL_SMOOTHING_WINDOW,
            smoothing_threshold=HCIConfig.TEMPORAL_SMOOTHING_THRESHOLD,
        )
        self._keyboard = KbController()
        self._fist_start_time: Optional[float] = None
        self._prev_palm: Optional[Tuple[float, float]] = None

    def detect(
        self,
        landmarks: List[Tuple[float, float, float]],
        handedness: str,
        **kwargs: Any,
    ) -> Optional[str]:
        threshold = HCIConfig.FINGER_EXTENSION_THRESHOLD
        is_fist = LandmarkUtils.is_fist(landmarks, handedness, threshold)

        if not is_fist:
            self._fist_start_time = None
            self._prev_palm = None
            return None

        now = time.time()
        if self._fist_start_time is None:
            self._fist_start_time = now
            self._prev_palm = LandmarkUtils.palm_center(landmarks)
            return None

        # Check hold duration
        held = now - self._fist_start_time
        if held < HCIConfig.TAB_SWITCH_HOLD_TIME:
            return None

        # Direction detection via horizontal hand velocity
        palm = LandmarkUtils.palm_center(landmarks)
        dt = kwargs.get("dt", 1.0 / 30.0)
        vx = 0.0
        if self._prev_palm:
            vx, _ = LandmarkUtils.hand_velocity(palm, self._prev_palm, dt)
        self._prev_palm = palm

        # Reset hold timer so it doesn't re-trigger immediately
        self._fist_start_time = None

        if vx < -HCIConfig.TAB_DIRECTION_VELOCITY_THRESHOLD:
            return "tab_back"  # Hand moved left
        return "tab_forward"

    def execute(self, gesture: str, **kwargs: Any) -> Optional[Dict[str, Any]]:
        try:
            if gesture == "tab_back":
                self._keyboard.press(Key.alt)
                self._keyboard.press(Key.shift)
                self._keyboard.press(Key.tab)
                self._keyboard.release(Key.tab)
                self._keyboard.release(Key.shift)
                self._keyboard.release(Key.alt)
                logger.debug("[TabSwitch] Alt+Shift+Tab")
            else:
                self._keyboard.press(Key.alt)
                self._keyboard.press(Key.tab)
                self._keyboard.release(Key.tab)
                self._keyboard.release(Key.alt)
                logger.debug("[TabSwitch] Alt+Tab")
        except Exception as e:
            logger.warning("[TabSwitch] Keyboard action failed: %s", e)
            return None

        return {"controller": self.name, "action": gesture}

    def reset(self) -> None:
        super().reset()
        self._fist_start_time = None
        self._prev_palm = None
