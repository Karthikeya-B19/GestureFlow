"""Gesture handler bridge — wraps CanvasInteractionController from sacred canvas_core."""

import logging
import sys
import os
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Ensure canvas_core can be imported (it may have relative imports)
_canvas_dir = os.path.dirname(os.path.abspath(__file__))
if _canvas_dir not in sys.path:
    sys.path.insert(0, _canvas_dir)

from apps.canvas.canvas_core import CanvasInteractionController  # noqa: E402


class GestureHandler:
    """Bridge between the PyQt6 canvas app and the sacred canvas engine.

    Creates and manages a CanvasInteractionController instance.
    Delegates frame processing and keyboard shortcuts.
    """

    def __init__(self) -> None:
        self._controller: Optional[CanvasInteractionController] = None
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize the canvas interaction controller."""
        if self._initialized:
            return True
        try:
            self._controller = CanvasInteractionController()
            self._initialized = True
            logger.info("Canvas gesture handler initialized")
            return True
        except Exception as e:
            logger.error("Failed to initialize canvas controller: %s", e)
            return False

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Process a camera frame through the canvas engine.

        Args:
            frame: BGR camera frame.

        Returns:
            Rendered canvas frame (BGR).
        """
        if not self._initialized:
            if not self.initialize():
                return frame

        try:
            return self._controller.process_frame(frame)
        except Exception as e:
            logger.error("Canvas process_frame error: %s", e)
            return frame

    def handle_key(self, key: str) -> None:
        """Handle keyboard shortcut for canvas actions.

        Key mappings:
            z → undo, y → redo, c → clear, s → save PNG, j → save JSON, l → new layer
        """
        if not self._initialized or self._controller is None:
            return

        key = key.lower()
        try:
            if key == "z":
                self._controller.state_manager.undo()
            elif key == "y":
                self._controller.state_manager.redo()
            elif key == "c":
                self._controller.state_manager.clear_canvas()
            elif key == "s":
                self._controller.state_manager.save_canvas_png()
            elif key == "j":
                self._controller.state_manager.save_canvas_json()
            elif key == "l":
                self._controller.state_manager.add_layer()
        except Exception as e:
            logger.warning("Canvas key '%s' handler error: %s", key, e)

    def cleanup(self) -> None:
        """Release resources."""
        if self._controller is not None:
            try:
                self._controller.cleanup()
            except Exception:
                pass
            self._controller = None
            self._initialized = False
