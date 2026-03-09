"""Volume controller — rock-on gesture + vertical hand movement."""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from apps.hci.config import HCIConfig
from apps.hci.controllers.base import BaseController
from core.landmark_utils import LandmarkUtils

logger = logging.getLogger(__name__)


def _init_audio():
    """Try to initialize Windows audio endpoint. Returns (endpoint, interface) or (None, None)."""
    try:
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)
        return volume, IAudioEndpointVolume
    except Exception as e:
        logger.warning("Audio device unavailable: %s", e)
        return None, None


class VolumeController(BaseController):
    """Rock-on gesture + move up/down → adjust system volume."""

    def __init__(self) -> None:
        super().__init__(
            name="Volume",
            cooldown_ms=HCIConfig.VOLUME_COOLDOWN,
            smoothing_window=HCIConfig.TEMPORAL_SMOOTHING_WINDOW,
            smoothing_threshold=HCIConfig.TEMPORAL_SMOOTHING_THRESHOLD,
        )
        self._volume_iface, _ = _init_audio()
        self._prev_palm: Optional[Tuple[float, float]] = None
        self._last_retry_time: float = 0.0

        if self._volume_iface is None:
            self.enabled = False
            logger.warning("[Volume] Disabled — no audio device found")

    def _retry_audio_init(self) -> None:
        """Periodically retry audio device initialization."""
        now = time.time()
        if now - self._last_retry_time < HCIConfig.VOLUME_DEVICE_RETRY_INTERVAL:
            return
        self._last_retry_time = now
        self._volume_iface, _ = _init_audio()
        if self._volume_iface is not None:
            self.enabled = True
            logger.info("[Volume] Audio device reconnected")

    def detect(
        self,
        landmarks: List[Tuple[float, float, float]],
        handedness: str,
        **kwargs: Any,
    ) -> Optional[str]:
        if self._volume_iface is None:
            self._retry_audio_init()
            if self._volume_iface is None:
                return None

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
        if self._volume_iface is None:
            return None

        try:
            current = self._volume_iface.GetMasterVolumeLevelScalar()
        except Exception:
            logger.warning("[Volume] Failed to read volume level")
            return None

        # Step scaling based on velocity
        landmarks = kwargs.get("landmarks")
        step_pct = HCIConfig.VOLUME_SMALL_STEP
        if landmarks and self._prev_palm:
            dt = kwargs.get("dt", 1.0 / 30.0)
            palm = LandmarkUtils.palm_center(landmarks)
            _, vy = LandmarkUtils.hand_velocity(palm, self._prev_palm, dt)
            if abs(vy) > HCIConfig.VOLUME_VELOCITY_LARGE:
                step_pct = HCIConfig.VOLUME_LARGE_STEP

        step = step_pct / 100.0

        if gesture == "volume_up":
            new_vol = min(1.0, current + step)
        else:
            new_vol = max(0.0, current - step)

        try:
            self._volume_iface.SetMasterVolumeLevelScalar(new_vol, None)
        except Exception:
            logger.warning("[Volume] Failed to set volume")
            return None

        volume_pct = int(new_vol * 100)
        logger.debug("[Volume] Set to %d%%", volume_pct)
        return {
            "controller": self.name,
            "action": gesture,
            "volume": volume_pct,
        }

    def reset(self) -> None:
        super().reset()
        self._prev_palm = None
