# Gesture Reference

All gestures are detected using **MediaPipe hand landmark geometry** — no custom ML models.

## GestureFlow HCI — System Control Gestures

| # | Gesture | Detection Logic | Action | Cooldown |
|---|---------|----------------|--------|----------|
| 1 | **Open Hand** | All 5 fingers extended | Move system cursor (index fingertip) | — |
| 2 | **Pinch** | Thumb tip ↔ index tip distance < 0.05 | Left click (hysteresis: engage 0.05, disengage 0.07) | 200ms |
| 3 | **Double Pinch** | Two pinches within 400ms | Double click | — |
| 4 | **Pinch Hold** | Pinch held > 300ms | Drag (mouseDown → mouseUp on release) | — |
| 5 | **Index Only** | Index extended, all others curled | Scroll up (velocity-scaled) | 150ms |
| 6 | **Index + Middle** | Index + middle extended, others curled | Scroll down (velocity-scaled) | 150ms |
| 7 | **Rock-on** 🤘 | Index + pinky extended, middle + ring curled | Volume control (up/down via hand movement) | 300ms |
| 8 | **Thumbs Up** 👍 | Thumb extended upward, all fingers curled | Play/Pause media | 1000ms |
| 9 | **Thumbs Down** 👎 | Thumb extended downward, all fingers curled | Mute/Unmute toggle | 1000ms |
| 10 | **Fist** ✊ (hold 500ms) | All fingers curled, held for 500ms | Alt+Tab (direction-aware: left = back) | 1500ms |
| 11 | **3 Fingers** | Index + middle + ring extended, no thumb/pinky | Brightness up (+10%) | 800ms |
| 12 | **4 Fingers** | Index + middle + ring + pinky extended, no thumb | Brightness down (-10%) | 800ms |

### Gesture Priority (highest first)
1. Fist → 2. Rock-on → 3. Thumbs Up → 4. Thumbs Down → 5. 3 Fingers → 6. 4 Fingers → 7. 1 Finger (Scroll Up) → 8. 2 Fingers (Scroll Down) → 9. Open Hand (Cursor)

### Temporal Smoothing
All gestures (except cursor movement) require **3 out of 5** consecutive frames of agreement before triggering. This eliminates false positives from transient hand positions.

### Gesture Transition Buffer
When switching between different gestures, **2 frames of IDLE** are required between detections. This prevents phantom triggers during hand transitions.

---

## GestureFlow Canvas — Drawing Gestures

The canvas uses the **sacred** `canvas_engine.py` gesture logic. These gestures are handled internally by `CanvasInteractionController`:

| Gesture | Action |
|---------|--------|
| Index finger point | Draw / interact |
| Pinch | Select / click |
| Open hand | Pan canvas |
| Fist | Shape tool |
| Various finger combos | Tool selection, color, brush size |

### Keyboard Shortcuts (Canvas)

| Key | Action |
|-----|--------|
| Z | Undo |
| Y | Redo |
| C | Clear canvas |
| S | Save PNG |
| J | Save JSON |
| L | New layer |
| F11 | Toggle fullscreen |
| Esc | Exit |

---

## Handedness

All thumb detection is **handedness-aware**:
- **Right hand**: Thumb tip X < thumb IP X = extended
- **Left hand**: Thumb tip X > thumb IP X = extended

MediaPipe reports handedness automatically. The system adapts in real-time.
