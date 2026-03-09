# Changelog

All notable changes to GestureFlow will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-09

### Added

#### GestureFlow HCI
- Cursor control via open hand gesture with adaptive EMA smoothing
- Click via pinch gesture with hysteresis (engage/disengage thresholds)
- Double-click support (two pinches within 400ms)
- Drag support (pinch hold > 300ms)
- Scroll up/down via finger count (1 finger = up, 2 fingers = down)
- Velocity-scaled scroll amount and scroll acceleration
- Volume control via rock-on gesture + hand vertical movement
- Proportional volume step scaling based on movement speed
- Media play/pause via thumbs up gesture
- Mute/unmute toggle via thumbs down gesture
- Tab switching via fist hold (500ms confirmation)
- Direction-aware tab switching (fist + hand direction)
- Brightness up/down via 3/4 finger gestures with step scaling
- System tray icon with context menu
- Semi-transparent overlay HUD with gesture feedback
- Click-through overlay mode
- Settings window with live preview (General, Gestures, Advanced tabs)
- JSON config persistence in %APPDATA%/GestureFlow/
- Overlay position memory across sessions

#### GestureFlow Canvas
- Full gesture-controlled drawing canvas (preserved from original project)
- 14+ geometric shapes (2D and 3D)
- Multi-layer support (up to 5 layers)
- Undo/redo (50-step history)
- Pressure-sensitive drawing via hand depth
- Shape cutting (knife tool)
- Object manipulation (move, scale, rotate)
- Save to PNG and JSON
- PyQt6 toolbar wrapper with keyboard shortcuts

#### Core Library
- MediaPipe Hands wrapper with lazy initialization
- Model complexity toggle (lite for HCI, full for canvas)
- Handedness-aware finger extension detection
- Gesture detection utilities (fist, rock-on, thumbs up/down, pinch)
- Adaptive coordinate smoothing (velocity-responsive EMA)
- One-Euro filter (opt-in alternative)
- Edge-aware screen coordinate mapping with cubic smoothstep
- Cursor dead zone for jitter elimination

#### Cross-Cutting
- Temporal smoothing (3/5 frame majority vote) on all gesture triggers
- Pinch hysteresis to prevent oscillation
- Gesture transition buffer (2 IDLE frames between switches)
- Confidence gating (reject MediaPipe detections < 0.6)
- Frame skipping when idle (CPU reduction ~40%)
- Graceful hardware degradation (audio, brightness, camera)
- Camera auto-reconnection (5s polling)
- Multi-threaded processing pipeline
- Structured logging (DEBUG/INFO/WARNING/ERROR)
- Single instance enforcement

#### Infrastructure
- PyInstaller specs for both apps (.exe packaging)
- GitHub Actions CI/CD (lint, test, build, release)
- CodeQL security scanning
- Pre-commit hooks (black, flake8, trailing-whitespace)
- Full documentation suite (gestures, installation, development, architecture)
