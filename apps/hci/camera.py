"""Camera capture thread with auto-detection, FPS limiting, and reconnection."""

import logging
import time
from collections import deque
from typing import Optional

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from apps.hci.config import HCIConfig

logger = logging.getLogger(__name__)


class CameraThread(QThread):
    """Background camera capture thread.

    Signals:
        frame_ready(np.ndarray): Emitted with each captured BGR frame.
        camera_error(str): Emitted when camera is unavailable.
        fps_updated(float): Emitted with rolling average FPS.
    """

    frame_ready = pyqtSignal(np.ndarray)
    camera_error = pyqtSignal(str)
    fps_updated = pyqtSignal(float)

    def __init__(
        self,
        camera_index: int = HCIConfig.CAMERA_INDEX,
        width: int = HCIConfig.CAMERA_WIDTH,
        height: int = HCIConfig.CAMERA_HEIGHT,
        max_fps: int = HCIConfig.MAX_FPS,
    ):
        super().__init__()
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.max_fps = max_fps
        self._running = False
        self._paused = False
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame_times: deque = deque(maxlen=30)

    def _open_camera(self) -> bool:
        """Try to open camera. Auto-detect index if configured one fails."""
        # Try configured index first
        for idx in [self.camera_index] + [i for i in range(5) if i != self.camera_index]:
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self._cap = cap
                self.camera_index = idx
                logger.info("Camera opened on index %d", idx)
                return True
            cap.release()

        logger.error("No camera found on indices 0-4")
        return False

    def run(self) -> None:
        """Main capture loop."""
        self._running = True

        if not self._open_camera():
            self.camera_error.emit("No camera detected")
            self._reconnect_loop()
            return

        frame_interval = 1.0 / self.max_fps

        while self._running:
            if self._paused:
                time.sleep(0.1)
                continue

            t_start = time.time()

            if self._cap is None or not self._cap.isOpened():
                self.camera_error.emit("Camera disconnected")
                self._reconnect_loop()
                if not self._running:
                    break
                continue

            ret, frame = self._cap.read()
            if not ret:
                # Retry a few times before calling it disconnected
                success = False
                for _ in range(3):
                    time.sleep(0.3)
                    ret, frame = self._cap.read()
                    if ret:
                        success = True
                        break
                if not success:
                    self.camera_error.emit("Camera read failed")
                    self._release()
                    self._reconnect_loop()
                    if not self._running:
                        break
                    continue

            self.frame_ready.emit(frame)

            # FPS tracking
            now = time.time()
            self._frame_times.append(now)
            if len(self._frame_times) >= 2:
                elapsed = self._frame_times[-1] - self._frame_times[0]
                if elapsed > 0:
                    fps = (len(self._frame_times) - 1) / elapsed
                    self.fps_updated.emit(fps)

            # FPS limiting
            elapsed = time.time() - t_start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        self._release()

    def _reconnect_loop(self) -> None:
        """Poll for camera reconnection every 5 seconds."""
        while self._running:
            time.sleep(5.0)
            if self._open_camera():
                logger.info("Camera reconnected")
                break

    def _release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def pause(self) -> None:
        self._paused = True
        logger.info("Camera paused")

    def resume(self) -> None:
        self._paused = False
        logger.info("Camera resumed")

    def stop(self) -> None:
        self._running = False
        self.wait(5000)
