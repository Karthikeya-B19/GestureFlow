"""Overlay HUD — frameless, translucent, always-on-top widget."""

import logging
from typing import Optional

from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QBrush, QPen
from PyQt6.QtWidgets import QWidget

from apps.hci.config import HCIConfig

logger = logging.getLogger(__name__)


class OverlayWidget(QWidget):
    """Semi-transparent overlay showing current gesture, confidence, FPS.

    Features:
    - Draggable, frameless, always-on-top
    - Optional click-through mode
    - Update throttle (only repaint on state change)
    - Position memory via save/restore
    """

    OVERLAY_W = 260
    OVERLAY_H = 100

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.OVERLAY_W, self.OVERLAY_H)

        # State
        self._gesture: str = "Idle"
        self._confidence: float = 0.0
        self._fps: float = 0.0
        self._mode: str = "Ready"
        self._dirty: bool = True
        self._opacity: float = HCIConfig.OVERLAY_OPACITY
        self._click_through: bool = HCIConfig.OVERLAY_CLICK_THROUGH
        self._show_fps: bool = HCIConfig.OVERLAY_SHOW_FPS

        # Drag support
        self._drag_pos: Optional[QPoint] = None

        # Feedback animation
        self._feedback_text: Optional[str] = None
        self._feedback_timer = QTimer(self)
        self._feedback_timer.setSingleShot(True)
        self._feedback_timer.timeout.connect(self._clear_feedback)

        if self._click_through:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Position — default bottom-right
        self.move(50, 50)

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
        if not self._dirty:
            return
        self._dirty = False

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

        # Gesture label
        painter.setPen(QColor(220, 220, 255))
        font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(12, 28, self._gesture)

        # Confidence bar
        bar_x, bar_y, bar_w, bar_h = 12, 38, self.width() - 24, 8
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(40, 40, 60))
        painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 4, 4)
        conf_color = self._confidence_color()
        painter.setBrush(conf_color)
        conf_w = int(bar_w * min(1.0, self._confidence))
        if conf_w > 0:
            painter.drawRoundedRect(bar_x, bar_y, conf_w, bar_h, 4, 4)

        # Mode label
        painter.setPen(QColor(160, 160, 200))
        small_font = QFont("Segoe UI", 9)
        painter.setFont(small_font)
        painter.drawText(12, 65, f"Mode: {self._mode}")

        # FPS
        if self._show_fps:
            painter.setPen(QColor(100, 100, 140))
            painter.drawText(self.width() - 70, 65, f"{self._fps:.1f} FPS")

        # Feedback flash
        if self._feedback_text:
            painter.setPen(QColor(100, 255, 150))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(12, 88, self._feedback_text)

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
