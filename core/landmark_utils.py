"""Landmark geometry helpers — finger extension, gestures, distances.

All functions operate on normalized MediaPipe landmarks (list of (x, y, z) tuples).
Handedness-aware where relevant (thumb detection flips for left hand).
"""

import math
from typing import Dict, List, Optional, Tuple

import numpy as np


class LandmarkUtils:
    """Static utility class for MediaPipe hand landmark analysis."""

    # MediaPipe landmark indices
    WRIST = 0
    THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
    INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
    MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
    RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
    PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

    FINGER_TIPS = [8, 12, 16, 20]
    FINGER_PIPS = [6, 10, 14, 18]
    FINGER_NAMES = ["index", "middle", "ring", "pinky"]

    @staticmethod
    def is_finger_extended(
        landmarks: List[Tuple[float, float, float]],
        finger_idx: int,
        threshold: float = 0.03,
    ) -> bool:
        """Check if a non-thumb finger is extended (tip above PIP joint).

        Args:
            landmarks: 21 MediaPipe hand landmarks (normalized x, y, z).
            finger_idx: 0=index, 1=middle, 2=ring, 3=pinky.
            threshold: Y-axis margin for extension detection.
        """
        tip = LandmarkUtils.FINGER_TIPS[finger_idx]
        pip = LandmarkUtils.FINGER_PIPS[finger_idx]
        return landmarks[tip][1] < landmarks[pip][1] - threshold

    @staticmethod
    def is_thumb_extended(
        landmarks: List[Tuple[float, float, float]],
        handedness: str = "Right",
    ) -> bool:
        """Check if thumb is extended, accounting for handedness.

        For Right hand: thumb tip X < thumb IP X (extended away from palm).
        For Left hand: thumb tip X > thumb IP X.
        """
        thumb_tip = landmarks[LandmarkUtils.THUMB_TIP]
        thumb_ip = landmarks[LandmarkUtils.THUMB_IP]
        thumb_mcp = landmarks[LandmarkUtils.THUMB_MCP]

        # Distance-based: thumb extended if tip is far from MCP
        dist = np.linalg.norm(
            np.array(thumb_tip[:2]) - np.array(thumb_mcp[:2])
        )
        if dist < 0.04:
            return False

        if handedness == "Right":
            return thumb_tip[0] < thumb_ip[0]
        else:
            return thumb_tip[0] > thumb_ip[0]

    @staticmethod
    def get_all_finger_states(
        landmarks: List[Tuple[float, float, float]],
        handedness: str = "Right",
        threshold: float = 0.03,
    ) -> Dict[str, bool]:
        """Compute extension state for all 5 fingers in one pass.

        Returns:
            Dict with keys: thumb, index, middle, ring, pinky.
        """
        states = {
            "thumb": LandmarkUtils.is_thumb_extended(landmarks, handedness),
        }
        for i, name in enumerate(LandmarkUtils.FINGER_NAMES):
            states[name] = LandmarkUtils.is_finger_extended(landmarks, i, threshold)
        return states

    @staticmethod
    def count_extended_fingers(
        landmarks: List[Tuple[float, float, float]],
        handedness: str = "Right",
        threshold: float = 0.03,
    ) -> int:
        """Count how many fingers are extended."""
        states = LandmarkUtils.get_all_finger_states(landmarks, handedness, threshold)
        return sum(1 for v in states.values() if v)

    @staticmethod
    def get_extended_finger_names(
        landmarks: List[Tuple[float, float, float]],
        handedness: str = "Right",
        threshold: float = 0.03,
    ) -> List[str]:
        """Return list of extended finger names."""
        states = LandmarkUtils.get_all_finger_states(landmarks, handedness, threshold)
        return [name for name, extended in states.items() if extended]

    @staticmethod
    def pinch_distance(landmarks: List[Tuple[float, float, float]]) -> float:
        """Euclidean distance between thumb tip and index finger tip (normalized)."""
        thumb = np.array(landmarks[LandmarkUtils.THUMB_TIP][:2])
        index = np.array(landmarks[LandmarkUtils.INDEX_TIP][:2])
        return float(np.linalg.norm(thumb - index))

    @staticmethod
    def landmark_distance(
        landmarks: List[Tuple[float, float, float]],
        idx1: int,
        idx2: int,
    ) -> float:
        """Euclidean distance between any two landmarks (2D, normalized)."""
        p1 = np.array(landmarks[idx1][:2])
        p2 = np.array(landmarks[idx2][:2])
        return float(np.linalg.norm(p1 - p2))

    @staticmethod
    def palm_center(
        landmarks: List[Tuple[float, float, float]],
    ) -> Tuple[float, float]:
        """Compute palm center as average of wrist + 4 MCP joints."""
        indices = [
            LandmarkUtils.WRIST,
            LandmarkUtils.INDEX_MCP,
            LandmarkUtils.MIDDLE_MCP,
            LandmarkUtils.RING_MCP,
            LandmarkUtils.PINKY_MCP,
        ]
        points = np.array([landmarks[i][:2] for i in indices])
        center = np.mean(points, axis=0)
        return (float(center[0]), float(center[1]))

    @staticmethod
    def hand_velocity(
        current_palm: Tuple[float, float],
        prev_palm: Tuple[float, float],
        dt: float,
    ) -> Tuple[float, float]:
        """Compute hand velocity (units/sec) from palm center positions.

        Returns:
            (vx, vy) velocity. Positive vy = moving downward in image coords.
        """
        if dt <= 0:
            return (0.0, 0.0)
        vx = (current_palm[0] - prev_palm[0]) / dt
        vy = (current_palm[1] - prev_palm[1]) / dt
        return (vx, vy)

    @staticmethod
    def is_fist(
        landmarks: List[Tuple[float, float, float]],
        handedness: str = "Right",
        threshold: float = 0.03,
    ) -> bool:
        """Detect closed fist — all fingers curled (not extended)."""
        states = LandmarkUtils.get_all_finger_states(landmarks, handedness, threshold)
        return not any(states.values())

    @staticmethod
    def is_rock_on(
        landmarks: List[Tuple[float, float, float]],
        handedness: str = "Right",
        threshold: float = 0.03,
    ) -> bool:
        """Detect rock-on gesture — index + pinky extended, middle + ring curled.

        Uses a lenient threshold for middle/ring so they must be clearly
        sticking out to block the gesture — makes detection much easier.
        """
        # Index and pinky: use the given (low) threshold — easy to detect as up
        index_up = LandmarkUtils.is_finger_extended(landmarks, 0, threshold)
        pinky_up = LandmarkUtils.is_finger_extended(landmarks, 3, threshold)

        # Middle and ring: use a MUCH higher threshold — only block if clearly extended
        curled_threshold = max(threshold, 0.04)
        middle_up = LandmarkUtils.is_finger_extended(landmarks, 1, curled_threshold)
        ring_up = LandmarkUtils.is_finger_extended(landmarks, 2, curled_threshold)

        return index_up and pinky_up and not middle_up and not ring_up

    @staticmethod
    def is_thumbs_up(
        landmarks: List[Tuple[float, float, float]],
        handedness: str = "Right",
        threshold: float = 0.03,
    ) -> bool:
        """Detect thumbs up — thumb extended upward, all other fingers curled."""
        states = LandmarkUtils.get_all_finger_states(landmarks, handedness, threshold)
        if not states["thumb"]:
            return False
        # All other fingers must be curled
        if states["index"] or states["middle"] or states["ring"] or states["pinky"]:
            return False
        # Thumb tip must be above thumb MCP (pointing up)
        return landmarks[LandmarkUtils.THUMB_TIP][1] < landmarks[LandmarkUtils.THUMB_MCP][1] + 0.01

    @staticmethod
    def is_thumbs_down(
        landmarks: List[Tuple[float, float, float]],
        handedness: str = "Right",
        threshold: float = 0.03,
    ) -> bool:
        """Detect thumbs down — thumb extended downward, all other fingers curled."""
        states = LandmarkUtils.get_all_finger_states(landmarks, handedness, threshold)
        if not states["thumb"]:
            return False
        if states["index"] or states["middle"] or states["ring"] or states["pinky"]:
            return False
        # Thumb tip must be below thumb MCP (pointing down)
        return landmarks[LandmarkUtils.THUMB_TIP][1] > landmarks[LandmarkUtils.THUMB_MCP][1] - 0.01

    @staticmethod
    def normalize_to_screen(
        norm_x: float,
        norm_y: float,
        screen_w: int,
        screen_h: int,
    ) -> Tuple[int, int]:
        """Map normalized (0-1) coordinates to screen pixel coordinates."""
        x = int(max(0, min(screen_w - 1, norm_x * screen_w)))
        y = int(max(0, min(screen_h - 1, norm_y * screen_h)))
        return (x, y)
