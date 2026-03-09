"""GestureFlow Canvas — main entry point.

Displays the gesture-controlled canvas with a PyQt6 toolbar.
Camera feed is processed through the sacred canvas engine.
"""

import logging
import sys
from typing import Optional

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QKeyEvent, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

from apps.canvas.gesture_handler import GestureHandler
from apps.canvas.ui.toolbar import CanvasToolbar
from apps.hci.camera import CameraThread
from apps.hci.config import HCIConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class GestureFlowCanvas(QMainWindow):
    """Main canvas application window.

    Shows rendered canvas output with a toolbar for tools, colors, and actions.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("GestureFlow Canvas")
        self.setMinimumSize(960, 720)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Display label
        self._display = QLabel()
        self._display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._display.setStyleSheet("background-color: #1a1a2e;")
        layout.addWidget(self._display, stretch=1)

        # Toolbar
        self._toolbar = CanvasToolbar(on_action=self._on_toolbar_action)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self._toolbar)

        # Canvas handler
        self._handler = GestureHandler()

        # Camera
        self._camera = CameraThread(
            camera_index=HCIConfig.CAMERA_INDEX,
            width=HCIConfig.CAMERA_WIDTH,
            height=HCIConfig.CAMERA_HEIGHT,
            max_fps=HCIConfig.MAX_FPS,
        )
        self._camera.frame_ready.connect(self._on_frame)
        self._camera.camera_error.connect(self._on_camera_error)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._camera.isRunning():
            self._camera.start()

    def closeEvent(self, event) -> None:
        self._camera.stop()
        self._handler.cleanup()
        super().closeEvent(event)

    def _on_frame(self, frame: np.ndarray) -> None:
        """Process camera frame and display result."""
        canvas_frame = self._handler.process_frame(frame)
        self._display_frame(canvas_frame)

    def _display_frame(self, frame: np.ndarray) -> None:
        """Convert numpy BGR frame to QPixmap and show on label."""
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        # Scale to fit display while maintaining aspect ratio
        scaled = pixmap.scaled(
            self._display.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._display.setPixmap(scaled)

    def _on_toolbar_action(self, action: str) -> None:
        """Handle toolbar action string (e.g., 'key:z', 'color:#FF4444')."""
        if action.startswith("key:"):
            key = action[4:]
            self._handler.handle_key(key)
        elif action.startswith("color:"):
            color_hex = action[6:]
            logger.info("Color selected: %s", color_hex)
            # Color handled by canvas engine internally via its toolbar
        elif action.startswith("brush_size:"):
            size = action[11:]
            logger.info("Brush size: %s", size)

    def _on_camera_error(self, msg: str) -> None:
        logger.error("Camera error: %s", msg)
        self._display.setText(f"Camera Error: {msg}")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.text()
        if key:
            self._handler.handle_key(key)
        if event.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        elif event.key() == Qt.Key.Key_Escape:
            self.close()
        super().keyPressEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    window = GestureFlowCanvas()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
