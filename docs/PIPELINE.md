# Pipeline — How GestureFlow Works

This guide walks through the end-to-end flow for both GestureFlow apps: **HCI** (system control) and **Canvas** (gesture drawing). It traces how frames move through capture, tracking, classification, and action layers.

```
Webcam → CameraThread → HandTracker → LandmarkUtils → GestureClassifier → Controller → OS / App Action
                                │                     │
                                └─────── CanvasInteractionController ───→ Rendered Canvas Frame
```

---

## HCI Pipeline (System Control)

1. **Capture (CameraThread)**  
   - Runs in its own `QThread`, opens the webcam (auto-detects indices), and emits `frame_ready` signals at a capped FPS.  
   - Handles disconnect/reconnect loops and feeds FPS stats back to the UI.

2. **Pre-processing (ProcessingWorker)**  
   - Receives frames off the main thread.  
   - Uses `core.hand_tracker.HandTracker` (MediaPipe Hands) to extract 21 landmarks, handedness, confidence, and bounding boxes.

3. **Gesture Analysis (GestureClassifier)**  
   - **Confidence gate:** drops low-confidence detections.  
   - **Frame skipping:** throttles stable/idle gestures to reduce CPU.  
   - **Priority identification:** `fist > rock_on > thumbs_up > thumbs_down > brightness (3/4 fingers or thumb+pinky) > scroll (1/2 fingers) > open_hand`.  
   - **Transition buffer:** requires a few idle frames before switching gestures to prevent flapping.  
   - **Temporal smoothing:** controller-level majority vote (3/5 frames) before acting.  
   - Relies on `core.landmark_utils` for finger states, pinch distance, and normalized coordinates.

4. **Action Dispatch (Controllers)**  
   - Routes to a specific controller:  
     - `CursorController` → cursor move, click, drag (pyautogui)  
     - `ScrollController` → velocity-scaled scroll (pyautogui)  
     - `VolumeController` → system volume (pycaw)  
     - `MediaController` → play/pause/mute (pynput keyboard media keys)  
     - `BrightnessController` → brightness up/down (screen_brightness_control)  
     - `TabSwitchController` → Alt+Tab with direction awareness  
   - Each controller enforces its own cooldowns and smoothing before executing OS actions.

5. **Feedback & UX (Main Thread)**  
   - The main PyQt6 loop renders the `OverlayWidget` (gesture name, confidence, FPS) and the HUD.  
   - `SystemTray` and `SettingsWindow` allow toggling and hot-reloading configuration without restarting.

6. **Configuration & Resilience**  
   - Settings live in `%APPDATA%/GestureFlow/config.json` and apply at runtime.  
   - Missing hardware (audio/brightness) gracefully disables affected controllers; camera disconnects auto-retry.

---

## Canvas Pipeline (Gesture Drawing)

1. **Capture**  
   - Shares the same `CameraThread` infrastructure to stream frames into the canvas app window.

2. **Canvas Engine Bridge**  
   - `GestureHandler` lazily initializes the sacred `CanvasInteractionController` (from `apps/canvas/canvas_core.py`).  
   - Each frame is passed through `CanvasInteractionController.process_frame`, which handles hand tracking, gesture interpretation, and rendering.

3. **Gesture-to-Canvas Actions**  
   - The canvas engine maps landmarks to drawing intents (freehand, shape placement, layer ops, undo/redo, save/export, etc.).  
   - Toolbar actions (`CanvasToolbar`) send shortcut strings (e.g., `key:z`, `brush_size:...`) back to `GestureHandler`, which forwards them to the engine’s state manager.

4. **Display**  
   - The engine returns a rendered BGR frame containing the canvas, HUD, and overlays.  
   - The main window converts it to a `QPixmap` and scales it to fit the viewport for smooth display.

---

## Shared Building Blocks

- **HandTracker** — MediaPipe Hands wrapper with lazy init; supports different model complexity (lite for HCI, full for Canvas).
- **LandmarkUtils** — Geometric helpers for finger extension, pinch distance, palm center, and screen normalization.
- **Smoothing** — EMA and temporal buffers for cursor movement, gesture stability, and noise suppression.
- **Config** — Tunables for camera size/FPS, thresholds, hysteresis, and frame skipping; loaded by both apps.
