"""PyQt6 toolbar for GestureFlow Canvas — tools, colors, actions."""

from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtWidgets import (
    QColorDialog,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QToolBar,
    QWidget,
    QLabel,
)


PALETTE_COLORS = [
    "#FFFFFF",  # White
    "#FF4444",  # Red
    "#44FF44",  # Green
    "#4488FF",  # Blue
    "#FFFF44",  # Yellow
    "#FF44FF",  # Magenta
    "#44FFFF",  # Cyan
]


class CanvasToolbar(QToolBar):
    """Toolbar with save, undo/redo, clear, color palette, brush size.

    Args:
        on_action: Callback ``(action_name: str) -> None`` for toolbar actions.
    """

    def __init__(self, on_action: Optional[Callable] = None, parent=None):
        super().__init__("Canvas Tools", parent)
        self._on_action = on_action
        self.setMovable(False)

        # --- Actions ---
        self._add_button("Save", "s")
        self._add_button("Undo", "z")
        self._add_button("Redo", "y")
        self._add_button("Clear", "c")
        self._add_button("Layer+", "l")
        self.addSeparator()

        # --- Color palette ---
        for color in PALETTE_COLORS:
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setStyleSheet(
                f"background-color: {color}; border: 2px solid #555; border-radius: 4px;"
            )
            btn.clicked.connect(lambda _, c=color: self._emit("color", c))
            self.addWidget(btn)

        # Custom color
        btn = QPushButton("...")
        btn.setFixedSize(28, 28)
        btn.setToolTip("Custom color")
        btn.clicked.connect(self._pick_color)
        self.addWidget(btn)
        self.addSeparator()

        # --- Brush size slider ---
        self.addWidget(QLabel("  Size:"))
        self._size_slider = QSlider(Qt.Orientation.Horizontal)
        self._size_slider.setRange(1, 30)
        self._size_slider.setValue(5)
        self._size_slider.setFixedWidth(120)
        self._size_slider.valueChanged.connect(lambda v: self._emit("brush_size", str(v)))
        self.addWidget(self._size_slider)

        self._size_label = QLabel(" 5")
        self._size_slider.valueChanged.connect(lambda v: self._size_label.setText(f" {v}"))
        self.addWidget(self._size_label)

    def _add_button(self, label: str, key: str) -> None:
        btn = QPushButton(label)
        btn.clicked.connect(lambda: self._emit("key", key))
        self.addWidget(btn)

    def _emit(self, action_type: str, value: str = "") -> None:
        if self._on_action:
            self._on_action(f"{action_type}:{value}")

    def _pick_color(self) -> None:
        color = QColorDialog.getColor()
        if color.isValid():
            self._emit("color", color.name())
