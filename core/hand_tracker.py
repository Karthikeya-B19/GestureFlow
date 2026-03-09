"""MediaPipe Hands wrapper with lazy initialization and configurable complexity."""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class HandResult:
    """Result from hand tracking for a single detected hand."""

    landmarks: List[Tuple[float, float, float]]
    handedness: str
    confidence: float
    bbox: Tuple[int, int, int, int]
    fingertip_positions: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)


class HandTracker:
    """Wrapper around MediaPipe Hands with lazy initialization.

    Args:
        max_num_hands: Maximum hands to detect.
        min_detection_confidence: Detection confidence threshold.
        min_tracking_confidence: Tracking confidence threshold.
        model_complexity: 0 for lite (fast, HCI), 1 for full (precise, canvas).
    """

    FINGERTIP_INDICES = {"thumb": 4, "index": 8, "middle": 12, "ring": 16, "pinky": 20}

    def __init__(
        self,
        max_num_hands: int = 1,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.5,
        model_complexity: int = 0,
    ):
        self.max_num_hands = max_num_hands
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.model_complexity = model_complexity
        self._mp_hands = mp.solutions.hands
        self._mp_drawing = mp.solutions.drawing_utils
        self._hands = None
        self._initialized = False

    def _lazy_init(self) -> bool:
        """Initialize MediaPipe Hands on first use."""
        if self._initialized:
            return self._hands is not None
        self._initialized = True
        try:
            self._hands = self._mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=self.max_num_hands,
                model_complexity=self.model_complexity,
                min_detection_confidence=self.min_detection_confidence,
                min_tracking_confidence=self.min_tracking_confidence,
            )
            logger.info(
                "MediaPipe Hands initialized (complexity=%d, det=%.2f, track=%.2f)",
                self.model_complexity,
                self.min_detection_confidence,
                self.min_tracking_confidence,
            )
            return True
        except Exception as e:
            logger.error("Failed to initialize MediaPipe Hands: %s", e)
            self._hands = None
            return False

    def process_frame(self, frame: np.ndarray) -> List[HandResult]:
        """Process a BGR frame and return detected hand results.

        Args:
            frame: BGR image from OpenCV.

        Returns:
            List of HandResult for each detected hand.
        """
        if not self._lazy_init():
            return []

        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb_frame)

        hands_data = []
        if results.multi_hand_landmarks and results.multi_handedness:
            for idx, (hand_landmarks, handedness_info) in enumerate(
                zip(results.multi_hand_landmarks, results.multi_handedness)
            ):
                landmarks = []
                x_coords, y_coords = [], []
                for lm in hand_landmarks.landmark:
                    landmarks.append((lm.x, lm.y, lm.z))
                    x_coords.append(lm.x * w)
                    y_coords.append(lm.y * h)

                x_min, x_max = int(min(x_coords)), int(max(x_coords))
                y_min, y_max = int(min(y_coords)), int(max(y_coords))
                bbox = (x_min, y_min, x_max - x_min, y_max - y_min)
                hand_label = handedness_info.classification[0].label
                confidence = handedness_info.classification[0].score

                fingertips = {}
                for finger_name, tip_idx in self.FINGERTIP_INDICES.items():
                    lm = landmarks[tip_idx]
                    fingertips[finger_name] = (lm[0] * w, lm[1] * h, lm[2])

                hands_data.append(
                    HandResult(
                        landmarks=landmarks,
                        handedness=hand_label,
                        confidence=confidence,
                        bbox=bbox,
                        fingertip_positions=fingertips,
                    )
                )

        return hands_data

    def draw_landmarks(self, frame: np.ndarray, hand_result: HandResult) -> np.ndarray:
        """Draw hand landmarks on a frame for visualization."""
        if not self._initialized or self._hands is None:
            return frame

        # Reconstruct MediaPipe landmark object for drawing
        landmark_proto = mp.solutions.hands.HandLandmark
        h, w, _ = frame.shape
        hand_landmarks = mp.framework.formats.landmark_pb2.NormalizedLandmarkList()
        for lm_tuple in hand_result.landmarks:
            landmark = hand_landmarks.landmark.add()
            landmark.x = lm_tuple[0]
            landmark.y = lm_tuple[1]
            landmark.z = lm_tuple[2]

        self._mp_drawing.draw_landmarks(
            frame,
            hand_landmarks,
            self._mp_hands.HAND_CONNECTIONS,
            self._mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
            self._mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=1),
        )
        return frame

    def release(self) -> None:
        """Release MediaPipe resources."""
        if self._hands is not None:
            self._hands.close()
            self._hands = None
            self._initialized = False
            logger.info("MediaPipe Hands released")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False
