"""System tray icon with context menu for GestureFlow HCI."""

import logging
from typing import Optional

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon, QApplication

logger = logging.getLogger(__name__)


class SystemTray(QSystemTrayIcon):
    """System tray icon with gesture toggle, overlay toggle, settings, quit.

    Args:
        app: The parent QApplication instance.
        icon_path: Path to tray icon file (optional).
    """

    def __init__(self, app: QApplication, icon_path: Optional[str] = None):
        icon = QIcon(icon_path) if icon_path else QIcon()
        super().__init__(icon, app)

        self._app = app
        self._overlay_visible = True
        self._gestures_enabled = True

        # Callbacks — set by main.py
        self.on_toggle_overlay = None
        self.on_open_settings = None
        self.on_toggle_gestures = None
        self.on_quit = None

        self._build_menu()
        self.activated.connect(self._on_activated)
        self.setToolTip("GestureFlow HCI")

    def _build_menu(self) -> None:
        menu = QMenu()

        self._overlay_action = QAction("Hide Overlay", self)
        self._overlay_action.triggered.connect(self._toggle_overlay)
        menu.addAction(self._overlay_action)

        self._settings_action = QAction("Settings", self)
        self._settings_action.triggered.connect(self._open_settings)
        menu.addAction(self._settings_action)

        menu.addSeparator()

        self._gesture_action = QAction("Disable Gestures", self)
        self._gesture_action.triggered.connect(self._toggle_gestures)
        menu.addAction(self._gesture_action)

        menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_overlay()

    def _toggle_overlay(self) -> None:
        self._overlay_visible = not self._overlay_visible
        self._overlay_action.setText(
            "Hide Overlay" if self._overlay_visible else "Show Overlay"
        )
        if self.on_toggle_overlay:
            self.on_toggle_overlay(self._overlay_visible)

    def _open_settings(self) -> None:
        if self.on_open_settings:
            self.on_open_settings()

    def _toggle_gestures(self) -> None:
        self._gestures_enabled = not self._gestures_enabled
        self._gesture_action.setText(
            "Disable Gestures" if self._gestures_enabled else "Enable Gestures"
        )
        if self.on_toggle_gestures:
            self.on_toggle_gestures(self._gestures_enabled)
        logger.info("Gestures %s", "enabled" if self._gestures_enabled else "disabled")

    def _quit(self) -> None:
        if self.on_quit:
            self.on_quit()
        else:
            QApplication.quit()
