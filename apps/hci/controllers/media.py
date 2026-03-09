"""Media controller — thumbs up → play/pause, thumbs down → mute/unmute."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from pynput.keyboard import Controller as KbController
from pynput.keyboard import Key

from apps.hci.config import HCIConfig
from apps.hci.controllers.base import BaseController
from core.landmark_utils import LandmarkUtils

logger = logging.getLogger(__name__)


class MediaController(BaseController):
    """Thumbs up → play/pause. Thumbs down → mute/unmute."""

    def __init__(self) -> None:
        super().__init__(
            name="Media",
            cooldown_ms=HCIConfig.MEDIA_COOLDOWN,
            smoothing_window=HCIConfig.TEMPORAL_SMOOTHING_WINDOW,
            smoothing_threshold=HCIConfig.TEMPORAL_SMOOTHING_THRESHOLD,
        )
        self._keyboard = KbController()

    def detect(
        self,
        landmarks: List[Tuple[float, float, float]],
        handedness: str,
        **kwargs: Any,
    ) -> Optional[str]:
        threshold = HCIConfig.FINGER_EXTENSION_THRESHOLD

        if LandmarkUtils.is_thumbs_up(landmarks, handedness, threshold):
            return "play_pause"
        if LandmarkUtils.is_thumbs_down(landmarks, handedness, threshold):
            return "mute_toggle"
        return None

    def execute(self, gesture: str, **kwargs: Any) -> Optional[Dict[str, Any]]:
        try:
            if gesture == "play_pause":
                self._keyboard.press(Key.media_play_pause)
                self._keyboard.release(Key.media_play_pause)
                logger.debug("[Media] Play/Pause toggled")
            elif gesture == "mute_toggle":
                self._keyboard.press(Key.media_volume_mute)
                self._keyboard.release(Key.media_volume_mute)
                logger.debug("[Media] Mute toggled")
        except Exception as e:
            logger.warning("[Media] Keyboard action failed: %s", e)
            return None

        return {"controller": self.name, "action": gesture}
