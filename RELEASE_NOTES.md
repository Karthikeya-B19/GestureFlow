# GestureFlow v1.1.0

**CV-Based Human Computer Interaction Suite** — Control your Windows PC with hand gestures using MediaPipe.

## What's New

### Volume Control — Now Works Everywhere
- Replaced pycaw audio interface with **Windows media key simulation** (`VK_VOLUME_UP` / `VK_VOLUME_DOWN`)
- Works on all Windows machines regardless of audio device detection issues
- Rock-on gesture 🤘 + move hand up/down to adjust volume

### Improved Gesture Detection
- **Rock-on 🤘 detection overhauled** — split thresholds so partially uncurled middle/ring fingers don't block the gesture
- **Relaxed all gesture thresholds** for more forgiving recognition — gestures trigger even with imprecise hand positions
- **Faster gesture transitions** — reduced idle buffer from 2 frames to 1

### New Gestures
- **Thumb + Pinky (🤙)** for brightness down — replaces the old 4-finger gesture, more ergonomic and distinct
- **Close button** on the overlay HUD — red "X" at top-right corner for clean app shutdown

### Bug Fixes
- Fixed **MediaPipe import crash** (`AttributeError: module 'mediapipe' has no attribute 'framework'`) on newer mediapipe versions
- Fixed **volume controller disabled** on machines where pycaw can't detect audio devices

### Tools
- Added **gesture calibration tool** (`scripts/calibrate_gestures.py`) — interactive CLI to capture per-user hand landmark data (optional, for advanced users)

## Gesture Reference

| Gesture | Action |
|---------|--------|
| Open hand ✋ | Cursor control |
| Pinch (thumb + index) | Click / Double-click / Drag |
| Index finger ☝️ | Scroll up |
| Index + middle ✌️ | Scroll down |
| Rock-on 🤘 + move up | Volume up |
| Rock-on 🤘 + move down | Volume down |
| Thumbs up 👍 | Play / Pause |
| Thumbs down 👎 | Mute / Unmute |
| Fist ✊ (hold) | Alt+Tab |
| 3 fingers (I+M+R) | Brightness up |
| Thumb + Pinky 🤙 | Brightness down |

## Download

- **GestureFlowHCI-v1.1.0-win64.zip** — System control app (standalone, no Python needed)
- **GestureFlowCanvas-v1.1.0-win64.zip** — Gesture drawing canvas app (standalone)

Extract and run the `.exe` inside.

## Requirements
- Windows 10/11
- Webcam
