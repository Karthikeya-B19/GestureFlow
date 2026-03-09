"""Base controller with temporal smoothing, cooldown, and enable/disable."""

import logging
import time
from abc import ABC, abstractmethod
from collections import Counter, deque
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class BaseController(ABC):
    """Abstract base for all HCI gesture controllers.

    Provides:
    - Cooldown enforcement (configurable ms)
    - Temporal smoothing (majority vote over N frames)
    - Enable/disable toggle
    - Structured logging

    Subclasses implement ``detect()`` and ``execute()``.
    """

    def __init__(
        self,
        name: str,
        cooldown_ms: int = 500,
        smoothing_window: int = 5,
        smoothing_threshold: int = 3,
    ):
        self.name = name
        self.cooldown_ms = cooldown_ms
        self.smoothing_window = smoothing_window
        self.smoothing_threshold = smoothing_threshold
        self.enabled = True
        self._last_trigger_time: float = 0.0
        self._gesture_history: deque = deque(maxlen=smoothing_window)

    def can_trigger(self) -> bool:
        """Check if enough time has passed since last trigger."""
        if not self.enabled:
            return False
        elapsed = (time.time() - self._last_trigger_time) * 1000
        return elapsed >= self.cooldown_ms

    def _record_trigger(self) -> None:
        """Mark current time as last trigger."""
        self._last_trigger_time = time.time()

    def _smooth_gesture(self, gesture: Optional[str]) -> Optional[str]:
        """Apply temporal majority-vote smoothing.

        Requires ``smoothing_threshold`` out of last ``smoothing_window``
        frames to agree on a gesture before accepting it.
        """
        self._gesture_history.append(gesture)
        if len(self._gesture_history) < self.smoothing_window:
            return None

        recent = list(self._gesture_history)[-self.smoothing_window :]
        counts = Counter(g for g in recent if g is not None)
        if not counts:
            return None

        best, cnt = counts.most_common(1)[0]
        if cnt >= self.smoothing_threshold:
            return best
        return None

    @abstractmethod
    def detect(
        self,
        landmarks: List[Tuple[float, float, float]],
        handedness: str,
        **kwargs: Any,
    ) -> Optional[str]:
        """Detect gesture from landmarks. Return gesture name or None."""

    @abstractmethod
    def execute(self, gesture: str, **kwargs: Any) -> Optional[Dict[str, Any]]:
        """Execute the action for a detected gesture. Return metadata dict."""

    def process(
        self,
        landmarks: List[Tuple[float, float, float]],
        handedness: str,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        """Full pipeline: detect → smooth → cooldown check → execute.

        Returns action metadata dict if triggered, else None.
        """
        if not self.enabled:
            return None

        raw_gesture = self.detect(landmarks, handedness, **kwargs)
        smoothed = self._smooth_gesture(raw_gesture)

        if smoothed is None:
            return None

        if not self.can_trigger():
            return None

        self._record_trigger()
        self._gesture_history.clear()

        logger.debug(
            "[%s] Triggered: %s (cooldown: %dms)",
            self.name,
            smoothed,
            self.cooldown_ms,
        )
        return self.execute(smoothed, **kwargs)

    def enable(self) -> None:
        self.enabled = True
        logger.info("[%s] Enabled", self.name)

    def disable(self) -> None:
        self.enabled = False
        logger.info("[%s] Disabled", self.name)

    def reset(self) -> None:
        """Reset internal state."""
        self._gesture_history.clear()
        self._last_trigger_time = 0.0
