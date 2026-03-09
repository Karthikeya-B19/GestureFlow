"""GestureFlow HCI — main entry point.

Wires camera thread, hand tracker, gesture classifier, overlay, tray, and settings.
Processing pipeline runs on a separate QThread to keep UI responsive.
"""

import logging
import sys
import time
from typing import Any, Dict, Optional

import cv2
import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QApplication

from apps.hci.camera import CameraThread
from apps.hci.config import HCIConfig
from apps.hci.gesture_classifier import GestureClassifier
from apps.hci.ui.overlay import OverlayWidget
from apps.hci.ui.settings import SettingsWindow, load_config, save_config
from apps.hci.ui.tray import SystemTray
from core.hand_tracker import HandTracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class ProcessingWorker(QObject):
    """Runs hand tracking + gesture classification on a background thread.

    Signals:
        gesture_detected(dict): Emitted with action metadata.
        gesture_label(str, float): Emitted with gesture name + confidence.
    """

    gesture_detected = pyqtSignal(dict)
    gesture_label = pyqtSignal(str, float)

    def __init__(self) -> None:
        super().__init__()
        self._tracker = HandTracker(
            max_num_hands=1,
            min_detection_confidence=HCIConfig.MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=HCIConfig.MIN_TRACKING_CONFIDENCE,
            model_complexity=HCIConfig.MODEL_COMPLEXITY,
        )
        self._classifier = GestureClassifier()
        self._last_time: float = time.time()

    @pyqtSlot(np.ndarray)
    def process_frame(self, frame: np.ndarray) -> None:
        """Process a single camera frame."""
        now = time.time()
        dt = now - self._last_time
        self._last_time = now

        results = self._tracker.process_frame(frame)
        if not results:
            self.gesture_label.emit("No Hand", 0.0)
            return

        hand = results[0]

        # Route through classifier
        action = self._classifier.classify(
            landmarks=hand.landmarks,
            handedness=hand.handedness,
            confidence=hand.confidence,
            dt=dt,
        )

        # Emit gesture label for overlay
        self.gesture_label.emit(
            action.get("action", "Idle") if action else "Idle",
            hand.confidence,
        )

        if action:
            self.gesture_detected.emit(action)

    def apply_config(self, config: Dict[str, Any]) -> None:
        """Hot-reload config to controllers."""
        classifier = self._classifier
        for key, ctrl in classifier._controllers.items():
            enabled_key = f"{key}_enabled"
            cooldown_key = f"{key}_cooldown"
            if enabled_key in config:
                if config[enabled_key]:
                    ctrl.enable()
                else:
                    ctrl.disable()
            if cooldown_key in config:
                ctrl.cooldown_ms = config[cooldown_key]

    def reset(self) -> None:
        self._classifier.reset()

    def enable_all(self) -> None:
        self._classifier.enable_all()

    def disable_all(self) -> None:
        self._classifier.disable_all()


class GestureFlowHCI:
    """Main application class — orchestrates all components."""

    def __init__(self) -> None:
        self._app = QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(False)

        self._config = load_config()

        # UI components
        self._overlay = OverlayWidget()
        self._tray = SystemTray(self._app)
        self._settings: Optional[SettingsWindow] = None

        # Camera thread
        camera_idx = self._config.get("camera_index", HCIConfig.CAMERA_INDEX)
        self._camera = CameraThread(camera_index=camera_idx)

        # Processing worker on separate thread
        self._proc_thread = QThread()
        self._worker = ProcessingWorker()
        self._worker.moveToThread(self._proc_thread)

        # Wire signals
        self._camera.frame_ready.connect(self._worker.process_frame)
        self._camera.fps_updated.connect(self._overlay.set_fps)
        self._camera.camera_error.connect(self._on_camera_error)
        self._worker.gesture_label.connect(self._on_gesture_label)
        self._worker.gesture_detected.connect(self._on_gesture_detected)

        # Tray callbacks
        self._tray.on_toggle_overlay = self._toggle_overlay
        self._tray.on_open_settings = self._open_settings
        self._tray.on_toggle_gestures = self._toggle_gestures
        self._tray.on_quit = self._quit

        # Apply saved config
        if self._config:
            self._apply_config(self._config)
            pos = self._config.get("overlay_position")
            if pos:
                self._overlay.restore_position(pos)

    def run(self) -> int:
        """Start the application."""
        logger.info("GestureFlow HCI starting...")

        self._proc_thread.start()
        self._camera.start()

        if not self._config.get("start_minimized", HCIConfig.START_MINIMIZED):
            self._overlay.show()

        self._tray.show()

        exit_code = self._app.exec()
        self._shutdown()
        return exit_code

    def _shutdown(self) -> None:
        logger.info("Shutting down...")
        self._camera.stop()
        self._proc_thread.quit()
        self._proc_thread.wait(3000)

        # Save overlay position
        self._config["overlay_position"] = self._overlay.get_position()
        save_config(self._config)

    def _toggle_overlay(self, visible: bool) -> None:
        if visible:
            self._overlay.show()
        else:
            self._overlay.hide()

    def _open_settings(self) -> None:
        if self._settings is None:
            self._settings = SettingsWindow(on_config_changed=self._on_config_saved)
        self._settings.show()
        self._settings.raise_()

    def _toggle_gestures(self, enabled: bool) -> None:
        if enabled:
            self._worker.enable_all()
            self._camera.resume()
            self._overlay.set_mode("Active")
        else:
            self._worker.disable_all()
            self._camera.pause()
            self._overlay.set_mode("Paused")

    def _on_config_saved(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._apply_config(config)

    def _apply_config(self, config: Dict[str, Any]) -> None:
        self._worker.apply_config(config)
        opacity = config.get("overlay_opacity", HCIConfig.OVERLAY_OPACITY)
        self._overlay.set_opacity(opacity)
        self._overlay.set_click_through(config.get("click_through", HCIConfig.OVERLAY_CLICK_THROUGH))

    @pyqtSlot(str, float)
    def _on_gesture_label(self, gesture: str, confidence: float) -> None:
        self._overlay.set_gesture(gesture, confidence)

    @pyqtSlot(dict)
    def _on_gesture_detected(self, action: dict) -> None:
        ctrl = action.get("controller", "")
        act = action.get("action", "")
        feedback = f"{ctrl}: {act}"
        self._overlay.show_feedback(feedback, 800)

    def _on_camera_error(self, msg: str) -> None:
        self._overlay.set_mode(f"Error: {msg}")
        logger.error("Camera: %s", msg)

    def _quit(self) -> None:
        self._app.quit()


def main() -> None:
    app = GestureFlowHCI()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
