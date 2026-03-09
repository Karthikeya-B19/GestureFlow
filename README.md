# GestureFlow

[![CI](https://github.com/Karthikeya-B19/gestureflow/actions/workflows/ci.yml/badge.svg)](https://github.com/Karthikeya-B19/gestureflow/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**CV-Based Human Computer Interaction Suite** — Control your Windows PC with hand gestures using MediaPipe.

Two standalone apps:
- **GestureFlow HCI** — System-level gesture control (cursor, scroll, volume, brightness, media, tab switching)
- **GestureFlow Canvas** — Gesture-controlled drawing canvas with shapes, layers, and pressure sensitivity

---

## Features

### GestureFlow HCI

| Gesture | Action |
|---------|--------|
| Open hand | Cursor control (adaptive smoothing, edge-aware mapping) |
| Pinch (thumb + index) | Click / Double-click / Drag |
| Index finger only | Scroll up (velocity-scaled) |
| Index + middle | Scroll down (velocity-scaled) |
| Rock-on 🤘 + move up | Volume up (proportional to speed) |
| Rock-on 🤘 + move down | Volume down |
| Thumbs up 👍 | Play / Pause |
| Thumbs down 👎 | Mute / Unmute |
| Fist ✊ (hold 500ms) | Alt+Tab (direction-aware) |
| 3 fingers (I+M+R) | Brightness up |
| 4 fingers (I+M+R+P) | Brightness down |

### GestureFlow Canvas

- Freehand drawing with pressure sensitivity
- 14+ geometric shapes (2D & 3D)
- Multi-layer support (up to 5 layers)
- Undo/redo (50-step history)
- Shape cutting, object manipulation
- Save to PNG & JSON

---

## Quick Start

### Option A — Run from source

```bash
git clone https://github.com/Karthikeya-B19/gestureflow.git
cd gestureflow
pip install -e .
gestureflow-hci        # Launch HCI app
gestureflow-canvas     # Launch Canvas app
```

### Option B — Download .exe

1. Go to [GitHub Releases](https://github.com/Karthikeya-B19/gestureflow/releases)
2. Download `GestureFlow-HCI.exe` or `GestureFlow-Canvas.exe`
3. Run — no Python installation required

---

## Architecture

```
Camera → MediaPipe Hands → Landmark Extraction → Gesture Classifier → Action Dispatcher
                                                         │
                                          ┌──────────────┼──────────────┐
                                          ▼              ▼              ▼
                                    [Cursor]       [Volume]       [Brightness]
                                    [Scroll]       [Media]        [TabSwitch]
```

### Optimizations

- **Temporal smoothing:** 3/5 frame majority vote prevents false positives
- **Adaptive cursor smoothing:** Velocity-responsive EMA (responsive during movement, smooth at rest)
- **Edge-aware screen mapping:** Cubic smoothstep for accurate cursor at screen edges
- **Frame skipping:** ~40% CPU reduction when hand is idle
- **Pinch hysteresis:** Separate engage/disengage thresholds prevent click oscillation
- **Graceful degradation:** Missing audio/brightness hardware auto-disables affected features
- **Camera reconnection:** Auto-recovers on camera disconnect/reconnect

---

## Requirements

- Windows 10/11
- Python 3.10+
- Webcam
- Dependencies listed in `requirements.txt`

---

## Development

```bash
pip install -e ".[dev]"
pre-commit install
pytest tests/ -v --cov=core --cov=apps
black --check --line-length 100 .
flake8 .
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for full development guide.

---

## Documentation

- [Gesture Reference](docs/GESTURES.md)
- [Installation Guide](docs/INSTALLATION.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [Architecture](docs/ARCHITECTURE.md)

---

## License

MIT License — see [LICENSE](LICENSE) for details.
