"""Overlay HUD — frameless, translucent, always-on-top widget with live camera."""

import logging
from typing import Optional

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QBrush, QPen, QPixmap
from PyQt6.QtWidgets import QWidget, QPushButton

from apps.hci.config import HCIConfig

logger = logging.getLogger(__name__)


class OverlayWidget(QWidget):
    """Semi-transparent overlay showing live camera feed + current gesture info.

    Features:
    - Small live camera preview with hand landmarks
    - Gesture label, confidence bar, FPS, mode
    - Draggable, frameless, always-on-top
    - Optional click-through mode
    - Position memory via save/restore
    """

    close_requested = pyqtSignal()

    CAM_W = 200
    CAM_H = 150
    INFO_H = 90
    OVERLAY_W = CAM_W + 20  # 10px padding on each side
    OVERLAY_H = CAM_H + INFO_H + 20  # cam + info + padding

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.OVERLAY_W, self.OVERLAY_H)

        # Close button
        self._close_btn = QPushButton("X", self)
        self._close_btn.setFixedSize(22, 22)
        self._close_btn.move(self.OVERLAY_W - 28, 4)
        self._close_btn.setStyleSheet(
            "QPushButton { background: rgba(200,50,50,180); color: white; "
            "border: none; border-radius: 11px; font-weight: bold; font-size: 12px; }"
            "QPushButton:hover { background: rgba(255,60,60,220); }"
        )
        self._close_btn.clicked.connect(self.close_requested.emit)

        # State
        self._gesture: str = "Idle"
        self._confidence: float = 0.0
        self._fps: float = 0.0
        self._mode: str = "Ready"
        self._dirty: bool = True
        self._opacity: float = HCIConfig.OVERLAY_OPACITY
        self._click_through: bool = HCIConfig.OVERLAY_CLICK_THROUGH
        self._show_fps: bool = HCIConfig.OVERLAY_SHOW_FPS

        # Camera preview
        self._cam_pixmap: Optional[QPixmap] = None

        # Drag support
        self._drag_pos: Optional[QPoint] = None

        # Feedback animation
        self._feedback_text: Optional[str] = None
        self._feedback_timer = QTimer(self)
        self._feedback_timer.setSingleShot(True)
        self._feedback_timer.timeout.connect(self._clear_feedback)

        if self._click_through:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Position — default top-left
        self.move(50, 50)

    def update_camera_feed(self, frame: np.ndarray) -> None:
        """Receive an annotated BGR frame and update the camera preview."""
        small = cv2.resize(frame, (self.CAM_W, self.CAM_H), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self._cam_pixmap = QPixmap.fromImage(qimg.copy())
        self._dirty = True
        self.update()

    def set_gesture(self, gesture: str, confidence: float = 0.0) -> None:
        if gesture != self._gesture or abs(confidence - self._confidence) > 0.05:
            self._gesture = gesture
            self._confidence = confidence
            self._dirty = True
            self.update()

    def set_fps(self, fps: float) -> None:
        if abs(fps - self._fps) > 0.5:
            self._fps = fps
            self._dirty = True
            self.update()

    def set_mode(self, mode: str) -> None:
        if mode != self._mode:
            self._mode = mode
            self._dirty = True
            self.update()

    def show_feedback(self, text: str, duration_ms: int = 1000) -> None:
        self._feedback_text = text
        self._feedback_timer.start(duration_ms)
        self._dirty = True
        self.update()

    def _clear_feedback(self) -> None:
        self._feedback_text = None
        self._dirty = True
        self.update()

    def set_opacity(self, value: float) -> None:
        self._opacity = max(0.3, min(1.0, value))
        self._dirty = True
        self.update()

    def set_click_through(self, enabled: bool) -> None:
        self._click_through = enabled
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, enabled)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background rounded rect
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        bg_color = QColor(20, 20, 30, int(255 * self._opacity))
        painter.fillPath(path, QBrush(bg_color))

        # Border
        painter.setPen(QPen(QColor(80, 80, 120, 150), 1))
        painter.drawPath(path)

        # --- Camera preview ---
        cam_x, cam_y = 10, 10
        # Draw camera background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(10, 10, 20))
        cam_path = QPainterPath()
        cam_path.addRoundedRect(cam_x, cam_y, self.CAM_W, self.CAM_H, 8, 8)
        painter.drawPath(cam_path)

        if self._cam_pixmap:
            # Clip to rounded rect
            painter.save()
            painter.setClipPath(cam_path)
            painter.drawPixmap(cam_x, cam_y, self._cam_pixmap)
            painter.restore()
        else:
            # Placeholder text
            painter.setPen(QColor(80, 80, 100))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(cam_x, cam_y, self.CAM_W, self.CAM_H,
                             Qt.AlignmentFlag.AlignCenter, "No Camera")

        # --- Info section below camera ---
        info_y = cam_y + self.CAM_H + 8

        # Gesture label
        painter.setPen(QColor(220, 220, 255))
        font = QFont("Segoe UI", 11, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(10, info_y + 14, self._gesture)

        # Confidence bar
        bar_x, bar_y = 10, info_y + 22
        bar_w, bar_h = self.CAM_W, 6
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(40, 40, 60))
        painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 3, 3)
        conf_color = self._confidence_color()
        painter.setBrush(conf_color)
        conf_w = int(bar_w * min(1.0, self._confidence))
        if conf_w > 0:
            painter.drawRoundedRect(bar_x, bar_y, conf_w, bar_h, 3, 3)

        # Mode + FPS row
        painter.setPen(QColor(160, 160, 200))
        small_font = QFont("Segoe UI", 8)
        painter.setFont(small_font)
        painter.drawText(10, info_y + 45, f"Mode: {self._mode}")

        if self._show_fps:
            painter.setPen(QColor(100, 100, 140))
            painter.drawText(self.CAM_W - 40, info_y + 45, f"{self._fps:.0f} FPS")

        # Feedback flash
        if self._feedback_text:
            painter.setPen(QColor(100, 255, 150))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(10, info_y + 62, self._feedback_text)

        self._dirty = False
        painter.end()

    def _confidence_color(self) -> QColor:
        if self._confidence > 0.8:
            return QColor(80, 200, 120)
        if self._confidence > 0.5:
            return QColor(200, 180, 50)
        return QColor(200, 80, 80)

    # --- Drag support ---
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None

    # --- Position save/restore ---
    def get_position(self) -> dict:
        pos = self.pos()
        return {"x": pos.x(), "y": pos.y()}

    def restore_position(self, pos: dict) -> None:
        x = pos.get("x", 50)
        y = pos.get("y", 50)
        self.move(x, y)
