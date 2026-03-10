"""GestureFlow Gesture Calibration Tool.

Run this to calibrate gesture recognition for YOUR hand.
It guides you through each gesture, captures landmark data,
and saves personalized thresholds to gesture_calibration.json.

Usage:
    python scripts/calibrate_gestures.py
"""

import json
import os
import sys
import time

import cv2
import numpy as np
import mediapipe as mp

# ── Gesture definitions ──────────────────────────────────────────────
GESTURES = [
    {
        "name": "open_hand",
        "display": "OPEN HAND",
        "desc": "Spread all 5 fingers wide",
    },
    {
        "name": "fist",
        "display": "FIST",
        "desc": "Close ALL fingers into a tight fist",
    },
    {
        "name": "one_finger",
        "display": "ONE FINGER (Index)",
        "desc": "Point INDEX finger up, curl all others",
    },
    {
        "name": "two_fingers",
        "display": "TWO FINGERS (Peace sign)",
        "desc": "INDEX + MIDDLE fingers up, curl the rest",
    },
    {
        "name": "three_fingers",
        "display": "THREE FINGERS",
        "desc": "INDEX + MIDDLE + RING up, thumb tucked",
    },
    {
        "name": "four_fingers",
        "display": "FOUR FINGERS",
        "desc": "All 4 fingers up, thumb tucked in",
    },
    {
        "name": "thumbs_up",
        "display": "THUMBS UP",
        "desc": "Thumb pointing UP, all other fingers closed",
    },
    {
        "name": "thumbs_down",
        "display": "THUMBS DOWN",
        "desc": "Thumb pointing DOWN, all other fingers closed",
    },
    {
        "name": "rock_on",
        "display": "ROCK ON / HORNS",
        "desc": "INDEX + PINKY up, MIDDLE + RING curled",
    },
]

# MediaPipe landmark indices
FINGER_TIPS = [8, 12, 16, 20]
FINGER_PIPS = [6, 10, 14, 18]
FINGER_NAMES = ["index", "middle", "ring", "pinky"]
THUMB_TIP, THUMB_IP, THUMB_MCP = 4, 3, 2


def compute_features(landmarks):
    """Compute feature vector from 21 hand landmarks.

    Returns dict with:
        - index_delta, middle_delta, ring_delta, pinky_delta: tip_y - pip_y
          (negative = finger extended, positive = finger curled)
        - thumb_mcp_dist: 2D distance from thumb tip to MCP
        - thumb_y_diff:   thumb_tip_y - thumb_mcp_y  (negative = pointing up)
        - thumb_x_diff:   thumb_tip_x - thumb_ip_x   (horizontal direction)
    """
    features = {}

    for i, name in enumerate(FINGER_NAMES):
        tip_y = landmarks[FINGER_TIPS[i]][1]
        pip_y = landmarks[FINGER_PIPS[i]][1]
        features[f"{name}_delta"] = tip_y - pip_y

    thumb_tip = landmarks[THUMB_TIP]
    thumb_ip = landmarks[THUMB_IP]
    thumb_mcp = landmarks[THUMB_MCP]

    features["thumb_mcp_dist"] = float(np.sqrt(
        (thumb_tip[0] - thumb_mcp[0]) ** 2 + (thumb_tip[1] - thumb_mcp[1]) ** 2
    ))
    features["thumb_y_diff"] = thumb_tip[1] - thumb_mcp[1]
    features["thumb_x_diff"] = thumb_tip[0] - thumb_ip[0]

    return features


def build_calibration(all_captures, handedness):
    """Build calibration data from captured samples."""
    feature_keys = [
        "index_delta", "middle_delta", "ring_delta", "pinky_delta",
        "thumb_mcp_dist", "thumb_y_diff", "thumb_x_diff",
    ]

    calibration = {
        "handedness": handedness,
        "gestures": {},
    }

    for gesture_name, samples in all_captures.items():
        gesture_data = {"sample_count": len(samples), "features": {}}

        for key in feature_keys:
            values = [s[key] for s in samples]
            gesture_data["features"][key] = {
                "mean": round(float(np.mean(values)), 6),
                "std": round(float(np.std(values)), 6),
                "min": round(float(np.min(values)), 6),
                "max": round(float(np.max(values)), 6),
            }

        calibration["gestures"][gesture_name] = gesture_data

    return calibration


def main():
    CAPTURE_SECONDS = 3

    # ── Open camera ──────────────────────────────────────────────────
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Could not open camera!")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        model_complexity=0,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
    )

    all_captures = {}
    detected_handedness = None

    print("=" * 50)
    print("  GestureFlow Gesture Calibration Tool")
    print("=" * 50)
    print()
    print("You'll be asked to perform 9 gestures.")
    print("For each gesture:")
    print("  1. Read the instructions on screen")
    print("  2. Hold the gesture with your hand visible")
    print("  3. Press SPACE to start capture")
    print(f"  4. Hold steady for {CAPTURE_SECONDS} seconds")
    print()
    print("Press ESC to skip a gesture, Q to quit.")
    print()

    for idx, gesture_info in enumerate(GESTURES):
        gesture_name = gesture_info["name"]
        display = gesture_info["display"]
        desc = gesture_info["desc"]

        print(f"\n[{idx + 1}/{len(GESTURES)}] {display}: {desc}")

        # ── Wait for SPACE ───────────────────────────────────────────
        capturing = False
        skipped = False
        quit_all = False

        while not capturing and not skipped and not quit_all:
            ret, frame = cap.read()
            if not ret:
                continue

            # Process for landmark display
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            if results.multi_hand_landmarks:
                for hlm in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        frame, hlm, mp_hands.HAND_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                        mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=1),
                    )

            # Draw instruction overlay
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (640, 100), (30, 30, 30), -1)
            cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

            cv2.putText(frame, f"[{idx + 1}/{len(GESTURES)}] {display}",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(frame, desc,
                        (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            hand_detected = results.multi_hand_landmarks is not None
            if hand_detected:
                status = "Hand DETECTED - Press SPACE to capture"
                color = (0, 255, 0)
            else:
                status = "Show your hand to the camera..."
                color = (0, 0, 255)
            cv2.putText(frame, status, (10, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
            cv2.putText(frame, "ESC=skip | Q=quit", (480, 95),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

            cv2.imshow("GestureFlow Calibration", frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord(' ') and hand_detected:
                capturing = True
            elif key == 27:  # ESC
                skipped = True
                print(f"  Skipped {gesture_name}")
            elif key == ord('q'):
                quit_all = True
                print("\nCalibration cancelled by user.")

        if quit_all:
            break
        if skipped:
            continue

        # ── Capture frames ───────────────────────────────────────────
        samples = []
        start_time = time.time()

        while time.time() - start_time < CAPTURE_SECONDS:
            ret, frame = cap.read()
            if not ret:
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            if results.multi_hand_landmarks and results.multi_handedness:
                hlm = results.multi_hand_landmarks[0]
                mp_drawing.draw_landmarks(
                    frame, hlm, mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=1),
                )

                hand_label = results.multi_handedness[0].classification[0].label
                if detected_handedness is None:
                    detected_handedness = hand_label

                landmarks = [(lm.x, lm.y, lm.z) for lm in hlm.landmark]
                features = compute_features(landmarks)
                samples.append(features)

            # Draw progress overlay
            elapsed = time.time() - start_time
            progress = min(elapsed / CAPTURE_SECONDS, 1.0)

            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (640, 70), (30, 30, 30), -1)
            cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

            cv2.putText(frame, f"CAPTURING: {display} ({len(samples)} samples)",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(frame, "Hold the gesture steady!",
                        (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

            # Progress bar
            bar_w = int(600 * progress)
            cv2.rectangle(frame, (20, 58), (620, 66), (100, 100, 100), -1)
            cv2.rectangle(frame, (20, 58), (20 + bar_w, 66), (0, 255, 0), -1)

            cv2.imshow("GestureFlow Calibration", frame)
            cv2.waitKey(1)

        if samples:
            all_captures[gesture_name] = samples
            print(f"  Captured {len(samples)} samples for {gesture_name}")
        else:
            print(f"  WARNING: No samples captured for {gesture_name}!")

    # ── Compute and save calibration ─────────────────────────────────
    if not all_captures:
        print("\nNo gestures calibrated. Exiting.")
        cap.release()
        cv2.destroyAllWindows()
        hands.close()
        return

    calibration = build_calibration(all_captures, detected_handedness or "Right")

    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "gesture_calibration.json",
    )
    with open(output_path, "w") as f:
        json.dump(calibration, f, indent=2)

    # ── Show completion screen ───────────────────────────────────────
    print(f"\nCalibration saved to: {output_path}")
    print(f"Gestures calibrated: {len(all_captures)}")
    for gname, samples in all_captures.items():
        print(f"  {gname}: {len(samples)} samples")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (640, 480), (30, 30, 30), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        cv2.putText(frame, "CALIBRATION COMPLETE!", (120, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        y = 140
        cv2.putText(frame, f"Gestures calibrated: {len(all_captures)}", (50, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        y += 30
        cv2.putText(frame, f"Hand detected: {detected_handedness}", (50, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        y += 30
        cv2.putText(frame, f"Saved to: gesture_calibration.json", (50, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        y += 40

        for gname, samples in all_captures.items():
            cv2.putText(frame, f"  {gname}: {len(samples)} samples", (50, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 200), 1)
            y += 22

        cv2.putText(frame, "Press any key to close", (180, 440),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        cv2.imshow("GestureFlow Calibration", frame)
        if cv2.waitKey(0) & 0xFF:
            break

    cap.release()
    cv2.destroyAllWindows()
    hands.close()

    print("\nRun the HCI app — it will automatically use your calibration data.")


if __name__ == "__main__":
    main()
