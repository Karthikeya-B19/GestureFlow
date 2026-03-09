"""Settings window — tabbed configuration UI for GestureFlow HCI."""

import json
import logging
import os
from typing import Any, Callable, Dict, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from apps.hci.config import HCIConfig

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", "."), "GestureFlow")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def load_config() -> Dict[str, Any]:
    """Load config from AppData JSON. Returns empty dict if missing."""
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Config load failed: %s", e)
        return {}


def save_config(config: Dict[str, Any]) -> None:
    """Save config dict to AppData JSON."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    logger.info("Config saved to %s", CONFIG_FILE)


class SettingsWindow(QWidget):
    """Tabbed settings window: General, Gestures, Advanced."""

    def __init__(self, on_config_changed: Optional[Callable] = None):
        super().__init__()
        self.setWindowTitle("GestureFlow Settings")
        self.setMinimumSize(480, 420)
        self._on_config_changed = on_config_changed
        self._config = load_config()

        layout = QVBoxLayout(self)
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._build_general_tab()
        self._build_gestures_tab()
        self._build_advanced_tab()

        # Buttons
        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        reset_btn = QPushButton("Reset Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        btn_row.addStretch()
        btn_row.addWidget(reset_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _build_general_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Camera
        cam_group = QGroupBox("Camera")
        cam_layout = QVBoxLayout(cam_group)
        row = QHBoxLayout()
        row.addWidget(QLabel("Camera Index:"))
        self._camera_idx = QSpinBox()
        self._camera_idx.setRange(0, 4)
        self._camera_idx.setValue(self._config.get("camera_index", HCIConfig.CAMERA_INDEX))
        row.addWidget(self._camera_idx)
        cam_layout.addLayout(row)
        layout.addWidget(cam_group)

        # Overlay
        ov_group = QGroupBox("Overlay")
        ov_layout = QVBoxLayout(ov_group)

        row = QHBoxLayout()
        row.addWidget(QLabel("Opacity:"))
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(30, 100)
        self._opacity_slider.setValue(int(self._config.get("overlay_opacity", HCIConfig.OVERLAY_OPACITY) * 100))
        row.addWidget(self._opacity_slider)
        self._opacity_label = QLabel(f"{self._opacity_slider.value()}%")
        self._opacity_slider.valueChanged.connect(lambda v: self._opacity_label.setText(f"{v}%"))
        row.addWidget(self._opacity_label)
        ov_layout.addLayout(row)

        self._show_fps_cb = QCheckBox("Show FPS")
        self._show_fps_cb.setChecked(self._config.get("show_fps", HCIConfig.OVERLAY_SHOW_FPS))
        ov_layout.addWidget(self._show_fps_cb)

        self._click_through_cb = QCheckBox("Click-through mode")
        self._click_through_cb.setChecked(self._config.get("click_through", HCIConfig.OVERLAY_CLICK_THROUGH))
        ov_layout.addWidget(self._click_through_cb)

        self._show_webcam_cb = QCheckBox("Show webcam preview")
        self._show_webcam_cb.setChecked(self._config.get("show_webcam", HCIConfig.OVERLAY_SHOW_WEBCAM))
        ov_layout.addWidget(self._show_webcam_cb)

        layout.addWidget(ov_group)

        self._start_minimized_cb = QCheckBox("Start minimized to tray")
        self._start_minimized_cb.setChecked(self._config.get("start_minimized", HCIConfig.START_MINIMIZED))
        layout.addWidget(self._start_minimized_cb)

        layout.addStretch()
        self._tabs.addTab(tab, "General")

    def _build_gestures_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._gesture_toggles = {}
        gestures = [
            ("cursor", "Cursor Control", HCIConfig.CLICK_COOLDOWN),
            ("scroll", "Scroll", HCIConfig.SCROLL_COOLDOWN),
            ("volume", "Volume", HCIConfig.VOLUME_COOLDOWN),
            ("media", "Media", HCIConfig.MEDIA_COOLDOWN),
            ("tab_switch", "Tab Switch", HCIConfig.TAB_SWITCH_COOLDOWN),
            ("brightness", "Brightness", HCIConfig.BRIGHTNESS_COOLDOWN),
        ]

        for key, label, default_cd in gestures:
            group = QGroupBox(label)
            gl = QHBoxLayout(group)

            cb = QCheckBox("Enabled")
            cb.setChecked(self._config.get(f"{key}_enabled", True))
            gl.addWidget(cb)

            gl.addWidget(QLabel("Cooldown (ms):"))
            sp = QSpinBox()
            sp.setRange(50, 5000)
            sp.setValue(self._config.get(f"{key}_cooldown", default_cd))
            gl.addWidget(sp)

            self._gesture_toggles[key] = (cb, sp)
            layout.addWidget(group)

        layout.addStretch()
        self._tabs.addTab(tab, "Gestures")

    def _build_advanced_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Temporal smoothing
        ts_group = QGroupBox("Temporal Smoothing")
        ts_layout = QVBoxLayout(ts_group)
        row = QHBoxLayout()
        row.addWidget(QLabel("Window:"))
        self._smooth_window = QSpinBox()
        self._smooth_window.setRange(1, 15)
        self._smooth_window.setValue(self._config.get("smoothing_window", HCIConfig.TEMPORAL_SMOOTHING_WINDOW))
        row.addWidget(self._smooth_window)
        row.addWidget(QLabel("Threshold:"))
        self._smooth_threshold = QSpinBox()
        self._smooth_threshold.setRange(1, 15)
        self._smooth_threshold.setValue(self._config.get("smoothing_threshold", HCIConfig.TEMPORAL_SMOOTHING_THRESHOLD))
        row.addWidget(self._smooth_threshold)
        ts_layout.addLayout(row)
        layout.addWidget(ts_group)

        # Cursor
        cursor_group = QGroupBox("Cursor")
        cl = QVBoxLayout(cursor_group)
        row = QHBoxLayout()
        row.addWidget(QLabel("Dead zone (px):"))
        self._dead_zone = QSpinBox()
        self._dead_zone.setRange(0, 20)
        self._dead_zone.setValue(self._config.get("dead_zone", HCIConfig.CURSOR_DEAD_ZONE))
        row.addWidget(self._dead_zone)
        cl.addLayout(row)

        self._adaptive_cb = QCheckBox("Adaptive smoothing")
        self._adaptive_cb.setChecked(self._config.get("adaptive_smoothing", HCIConfig.ADAPTIVE_SMOOTHING))
        cl.addWidget(self._adaptive_cb)

        self._frame_skip_cb = QCheckBox("Frame skipping when idle")
        self._frame_skip_cb.setChecked(self._config.get("frame_skip", HCIConfig.FRAME_SKIP_ENABLED))
        cl.addWidget(self._frame_skip_cb)

        layout.addWidget(cursor_group)

        # Confidence
        conf_group = QGroupBox("Confidence")
        confl = QVBoxLayout(conf_group)
        row = QHBoxLayout()
        row.addWidget(QLabel("Min confidence:"))
        self._conf_slider = QSlider(Qt.Orientation.Horizontal)
        self._conf_slider.setRange(30, 95)
        self._conf_slider.setValue(int(self._config.get("min_confidence", HCIConfig.LOW_CONFIDENCE_THRESHOLD) * 100))
        row.addWidget(self._conf_slider)
        self._conf_label = QLabel(f"{self._conf_slider.value()}%")
        self._conf_slider.valueChanged.connect(lambda v: self._conf_label.setText(f"{v}%"))
        row.addWidget(self._conf_label)
        confl.addLayout(row)
        layout.addWidget(conf_group)

        layout.addStretch()
        self._tabs.addTab(tab, "Advanced")

    def _collect_config(self) -> Dict[str, Any]:
        """Gather all UI values into config dict."""
        config = {
            "camera_index": self._camera_idx.value(),
            "overlay_opacity": self._opacity_slider.value() / 100.0,
            "show_fps": self._show_fps_cb.isChecked(),
            "click_through": self._click_through_cb.isChecked(),
            "show_webcam": self._show_webcam_cb.isChecked(),
            "start_minimized": self._start_minimized_cb.isChecked(),
            "smoothing_window": self._smooth_window.value(),
            "smoothing_threshold": self._smooth_threshold.value(),
            "dead_zone": self._dead_zone.value(),
            "adaptive_smoothing": self._adaptive_cb.isChecked(),
            "frame_skip": self._frame_skip_cb.isChecked(),
            "min_confidence": self._conf_slider.value() / 100.0,
        }
        for key, (cb, sp) in self._gesture_toggles.items():
            config[f"{key}_enabled"] = cb.isChecked()
            config[f"{key}_cooldown"] = sp.value()
        return config

    def _save(self) -> None:
        self._config = self._collect_config()
        save_config(self._config)
        if self._on_config_changed:
            self._on_config_changed(self._config)

    def _reset_defaults(self) -> None:
        """Reset all fields to HCIConfig defaults."""
        self._camera_idx.setValue(HCIConfig.CAMERA_INDEX)
        self._opacity_slider.setValue(int(HCIConfig.OVERLAY_OPACITY * 100))
        self._show_fps_cb.setChecked(HCIConfig.OVERLAY_SHOW_FPS)
        self._click_through_cb.setChecked(HCIConfig.OVERLAY_CLICK_THROUGH)
        self._show_webcam_cb.setChecked(HCIConfig.OVERLAY_SHOW_WEBCAM)
        self._start_minimized_cb.setChecked(HCIConfig.START_MINIMIZED)
        self._smooth_window.setValue(HCIConfig.TEMPORAL_SMOOTHING_WINDOW)
        self._smooth_threshold.setValue(HCIConfig.TEMPORAL_SMOOTHING_THRESHOLD)
        self._dead_zone.setValue(HCIConfig.CURSOR_DEAD_ZONE)
        self._adaptive_cb.setChecked(HCIConfig.ADAPTIVE_SMOOTHING)
        self._frame_skip_cb.setChecked(HCIConfig.FRAME_SKIP_ENABLED)
        self._conf_slider.setValue(int(HCIConfig.LOW_CONFIDENCE_THRESHOLD * 100))
        for key, (cb, sp) in self._gesture_toggles.items():
            cb.setChecked(True)

    def get_config(self) -> Dict[str, Any]:
        return dict(self._config)
