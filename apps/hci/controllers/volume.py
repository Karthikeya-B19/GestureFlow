"""Volume controller — rock-on gesture + vertical hand movement.

Uses Windows media key simulation (VK_VOLUME_UP / VK_VOLUME_DOWN)
which works regardless of audio device detection via pycaw.
"""

import ctypes
import logging
from typing import Any, Dict, List, Optional, Tuple

from apps.hci.config import HCIConfig
from apps.hci.controllers.base import BaseController
from core.landmark_utils import LandmarkUtils

logger = logging.getLogger(__name__)

# Windows virtual key codes for volume
VK_VOLUME_UP = 0xAF
VK_VOLUME_DOWN = 0xAE
KEYEVENTF_KEYUP = 0x0002


def _press_volume_key(vk_code: int) -> None:
    """Simulate a volume key press+release via Windows API."""
    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


class VolumeController(BaseController):
    """Rock-on + move up/down → adjust system volume via media keys."""

    def __init__(self) -> None:
        super().__init__(
            name="Volume",
            cooldown_ms=HCIConfig.VOLUME_COOLDOWN,
            smoothing_window=HCIConfig.TEMPORAL_SMOOTHING_WINDOW,
            smoothing_threshold=HCIConfig.TEMPORAL_SMOOTHING_THRESHOLD,
        )
        self._prev_palm: Optional[Tuple[float, float]] = None
        logger.info("[Volume] Using Windows media keys for volume control")

    def detect(
        self,
        landmarks: List[Tuple[float, float, float]],
        handedness: str,
        **kwargs: Any,
    ) -> Optional[str]:
        # Detect rock-on gesture (index + pinky extended, middle + ring curled)
        if not LandmarkUtils.is_rock_on(landmarks, handedness, HCIConfig.FINGER_EXTENSION_THRESHOLD):
            self._prev_palm = None
            return None

        palm = LandmarkUtils.palm_center(landmarks)
        if self._prev_palm is None:
            self._prev_palm = palm
            return None

        dt = kwargs.get("dt", 1.0 / 30.0)
        _, vy = LandmarkUtils.hand_velocity(palm, self._prev_palm, dt)
        self._prev_palm = palm

        if abs(vy) < HCIConfig.VOLUME_VELOCITY_THRESHOLD:
            return None

        # Negative vy = hand moving up (volume up in screen coords)
        return "volume_up" if vy < 0 else "volume_down"

    def execute(self, gesture: str, **kwargs: Any) -> Optional[Dict[str, Any]]:
        # Send volume key press(es) — each press = ~2% volume change
        landmarks = kwargs.get("landmarks")
        presses = 1
        if landmarks and self._prev_palm:
            dt = kwargs.get("dt", 1.0 / 30.0)
            palm = LandmarkUtils.palm_center(landmarks)
            _, vy = LandmarkUtils.hand_velocity(palm, self._prev_palm, dt)
            if abs(vy) > HCIConfig.VOLUME_VELOCITY_LARGE:
                presses = 3

        vk = VK_VOLUME_UP if gesture == "volume_up" else VK_VOLUME_DOWN
        for _ in range(presses):
            _press_volume_key(vk)

        logger.debug("[Volume] %s (%d presses)", gesture, presses)
        return {
            "controller": self.name,
            "action": gesture,
            "presses": presses,
        }

    def reset(self) -> None:
        super().reset()
        self._prev_palm = None
