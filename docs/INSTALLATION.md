# Installation Guide

## Prerequisites

- **Python 3.10+** (3.10, 3.11, or 3.12 recommended)
- **Windows 10/11** (required for pycaw audio, screen brightness control)
- **Webcam** (built-in or USB)

## Install from Source

```bash
# Clone the repository
git clone https://github.com/Karthikeya-B19/Robotic-vision.git
cd Robotic-vision/project_final

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in editable mode (optional — enables CLI commands)
pip install -e .
```

## Running the Apps

### GestureFlow HCI (System Control)
```bash
# Via module
python -m apps.hci.main

# Or via CLI entry point (if installed with pip install -e .)
gestureflow-hci
```

### GestureFlow Canvas (Drawing)
```bash
# Via module
python -m apps.canvas.main

# Or via CLI entry point
gestureflow-canvas
```

## Pre-built Executables

Download from [Releases](https://github.com/Karthikeya-B19/Robotic-vision/releases):
- `GestureFlowHCI.exe` — System control app (standalone, no Python needed)
- `GestureFlowCanvas.exe` — Drawing canvas app (standalone)

## Building Executables

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Build both apps
scripts\build_all.bat

# Or individually
pyinstaller scripts/build_hci.spec --clean -y
pyinstaller scripts/build_canvas.spec --clean -y
```

Output: `dist/hci/GestureFlowHCI.exe` and `dist/canvas/GestureFlowCanvas.exe`

## Troubleshooting

### "No camera detected"
- Check webcam is connected and not in use by another app
- Try a different camera index in Settings → General → Camera Index
- On some systems, try running as administrator

### Volume control
- Volume uses Windows media key simulation — works on all machines
- If volume doesn't respond, check that your system handles media keys
- No special audio device setup required

### "Display does not support software brightness"
- External monitors via HDMI may not support software brightness control
- Brightness controller auto-disables on unsupported displays
- Works reliably on laptop built-in displays

### MediaPipe initialization slow
- First frame takes 2-3 seconds as MediaPipe loads model weights
- Subsequent frames are fast (~30+ FPS)
- Overlay shows "Initializing..." during first load

### High CPU usage
- Enable frame skipping in Settings → Advanced
- Reduce MAX_FPS to 15
- Close other camera-using applications
