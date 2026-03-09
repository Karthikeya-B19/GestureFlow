# Development Guide

## Setup

```bash
# Clone and create venv
git clone https://github.com/Karthikeya-B19/Robotic-vision.git
cd Robotic-vision/project_final
python -m venv venv
venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .

# Setup pre-commit hooks
pre-commit install
```

## Code Style

- **Formatter**: Black (line-length=100)
- **Linter**: Flake8
- **Pre-commit**: Runs automatically on `git commit`

```bash
# Manual formatting
black --line-length 100 .

# Manual linting
flake8 .
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ -v --cov=core --cov=apps

# Specific test file
python -m pytest tests/test_landmark_utils.py -v
```

## Project Structure

```
project_final/
├── apps/
│   ├── hci/                  # GestureFlow HCI app
│   │   ├── main.py           # Entry point
│   │   ├── camera.py         # Camera thread (QThread)
│   │   ├── config.py         # All thresholds/settings
│   │   ├── gesture_classifier.py  # Priority routing
│   │   ├── controllers/      # Gesture action handlers
│   │   │   ├── base.py       # BaseController ABC
│   │   │   ├── cursor.py     # Cursor + click/drag
│   │   │   ├── scroll.py     # Scroll up/down
│   │   │   ├── volume.py     # Volume (pycaw)
│   │   │   ├── media.py      # Play/pause/mute
│   │   │   ├── tab_switch.py # Alt+Tab
│   │   │   └── brightness.py # Screen brightness
│   │   └── ui/               # PyQt6 UI
│   │       ├── tray.py       # System tray icon
│   │       ├── overlay.py    # HUD overlay
│   │       └── settings.py   # Settings window
│   └── canvas/               # GestureFlow Canvas app
│       ├── main.py           # Entry point
│       ├── canvas_core.py    # Sacred code (DO NOT MODIFY)
│       ├── gesture_handler.py # Bridge to canvas engine
│       └── ui/
│           └── toolbar.py    # PyQt6 toolbar
├── core/                     # Shared library
│   ├── hand_tracker.py       # MediaPipe wrapper
│   ├── landmark_utils.py     # Geometry helpers
│   ├── smoothing.py          # EMA, One-Euro filters
│   └── coordinate_mapper.py  # Screen mapping
├── tests/                    # Unit tests
├── scripts/                  # Build scripts
├── docs/                     # Documentation
└── assets/                   # Icons, resources
```

## Git Workflow

- **Branch naming**: `feature/`, `fix/`, `chore/`, `docs/`
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/)
  - `feat(core): add One-Euro filter`
  - `fix(hci): prevent cursor jitter at edges`
  - `docs: update gesture reference`
- **PR process**: Create PR → CI passes → review → merge

## Adding a New Gesture Controller

1. Create `apps/hci/controllers/my_controller.py`
2. Extend `BaseController` — implement `detect()` and `execute()`
3. Add config constants to `apps/hci/config.py`
4. Register in `apps/hci/gesture_classifier.py` `_identify_gesture()` + `_dispatch()`
5. Add to `apps/hci/controllers/__init__.py`
6. Add tests to `tests/test_controllers.py`
7. Update `docs/GESTURES.md`

## Release Process

1. Update `CHANGELOG.md`
2. Bump version in `pyproject.toml`
3. Create git tag: `git tag v1.x.x`
4. Push tag: `git push origin v1.x.x`
5. GitHub Actions builds .exe and creates release
