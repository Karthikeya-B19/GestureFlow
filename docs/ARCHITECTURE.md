# Architecture

## System Overview

GestureFlow consists of two standalone applications sharing a common core library:

```
┌──────────────────────────────┐    ┌──────────────────────────────┐
│      GestureFlow HCI         │    │     GestureFlow Canvas       │
│  (System Control)            │    │  (Gesture Drawing)           │
│                              │    │                              │
│  ┌────────┐ ┌─────────────┐ │    │  ┌────────┐ ┌────────────┐  │
│  │ Camera │→│ Processing  │ │    │  │ Camera │→│ Canvas     │  │
│  │ Thread │ │ Worker      │ │    │  │ Thread │ │ Engine     │  │
│  └────────┘ │             │ │    │  └────────┘ │ (Sacred)   │  │
│             │ HandTracker │ │    │             └────────────┘  │
│             │ Classifier  │ │    │             ┌────────────┐  │
│             │ Controllers │ │    │             │ Gesture    │  │
│             └──────┬──────┘ │    │             │ Handler    │  │
│                    │        │    │             └────────────┘  │
│  ┌─────────────────┘        │    │                              │
│  │ ┌───────┐ ┌─────────┐   │    │  ┌──────────────────────┐   │
│  │ │ Tray  │ │ Overlay │   │    │  │ PyQt6 Window +       │   │
│  │ │ Icon  │ │ HUD     │   │    │  │ Toolbar              │   │
│  │ └───────┘ └─────────┘   │    │  └──────────────────────┘   │
│  │           ┌──────────┐   │    └──────────────────────────────┘
│  │           │ Settings │   │
│  │           └──────────┘   │
└──────────────────────────────┘

        ┌──────────────────┐
        │   Core Library   │
        │                  │
        │ • HandTracker    │
        │ • LandmarkUtils  │
        │ • Smoothing      │
        │ • ScreenMapper   │
        └──────────────────┘
```

## Data Flow — HCI App

```
Webcam → CameraThread (QThread)
           │
           │ frame_ready signal
           ▼
      ProcessingWorker (QThread)
           │
           ├─ HandTracker.process_frame(frame)
           │   → List[HandResult] (landmarks, handedness, confidence)
           │
           ├─ GestureClassifier.classify(landmarks, handedness, confidence)
           │   │
           │   ├─ _identify_gesture() — priority-based detection
           │   ├─ _check_transition() — transition buffer
           │   ├─ _should_skip_frame() — frame skipping
           │   └─ _dispatch() → Controller.process()
           │       │
           │       ├─ BaseController.detect() — gesture-specific logic
           │       ├─ _smooth_gesture() — temporal majority vote (3/5)
           │       ├─ can_trigger() — cooldown check
           │       └─ BaseController.execute() — system action
           │           │
           │           ├─ pyautogui.moveTo() / click() / scroll()
           │           ├─ pynput keyboard (media keys, Alt+Tab)
           │           ├─ pycaw (volume)
           │           └─ screen_brightness_control
           │
           │ gesture_detected signal
           ▼
      Main Thread (PyQt6 event loop)
           │
           ├─ OverlayWidget — shows gesture, confidence, FPS
           ├─ SystemTray — menu, toggle
           └─ SettingsWindow — live config

```

## Threading Model

| Thread | Responsibility | Communication |
|--------|---------------|---------------|
| **Main** | PyQt6 event loop, UI rendering | Receives signals |
| **CameraThread** | OpenCV capture, FPS limiting | Emits `frame_ready` |
| **ProcessingWorker** | MediaPipe + gesture classification | Emits `gesture_detected` |

All thread-to-UI communication uses Qt signals/slots (thread-safe).

## Gesture Classification Pipeline

```
Landmarks → Confidence Gate → Frame Skip Check → Identify Gesture
     → Transition Buffer → Controller.detect() → Temporal Smoothing
     → Cooldown Check → Controller.execute() → System Action
```

### Priority Resolution
When multiple gestures could match (e.g., a fist and "no fingers extended" overlap), the classifier evaluates in strict priority order and returns the first match.

### Temporal Smoothing
```
Frame buffer (deque, size=5):
  [rock_on, rock_on, idle, rock_on, rock_on]
  
Counter: rock_on=4, idle=1
Best: rock_on (4 ≥ threshold 3) → ACCEPT
```

### Pinch Hysteresis
```
State: not_engaged
  pinch_distance < 0.05 → ENGAGE (click pending)
State: engaged
  pinch_distance > 0.07 → DISENGAGE (click fired)
  held > 300ms → DRAG mode
```

## Configuration

Config stored at `%APPDATA%/GestureFlow/config.json`. All settings hot-reload via the settings window — no restart required.

## Sacred Code

`apps/canvas/canvas_core.py` is a byte-for-byte copy of the original `canvas_engine.py`. It must **never** be modified. The `GestureHandler` class wraps it with a clean interface for the PyQt6 app.
