"""Screen coordinate mapping with edge-aware margins and dead zone.

Ported from the CoordinateMappingLayer pattern in canvas_engine.py.
Maps normalized hand coordinates to screen pixel positions with
non-linear edge compensation using cubic smoothstep blending.
"""

import math
from typing import Tuple


class ScreenMapper:
    """Maps normalized hand coordinates (0-1) to screen pixel coordinates.

    Features:
    - Non-linear margin blending at screen edges (cubic smoothstep)
    - Configurable dead zone to prevent micro-movements
    - Coordinate clamping to screen bounds

    Args:
        screen_w: Screen width in pixels.
        screen_h: Screen height in pixels.
        margin_center: Margin factor in center of screen (default 0.05).
        margin_edge: Margin factor at screen edges (default 0.015).
        blend_zone: Blend zone width for edge transition (default 0.15).
        dead_zone: Pixel radius below which cursor movement is suppressed.
        flip_x: Whether to mirror X axis (for webcam mirror effect).
    """

    def __init__(
        self,
        screen_w: int,
        screen_h: int,
        margin_center: float = 0.05,
        margin_edge: float = 0.015,
        blend_zone: float = 0.15,
        dead_zone: int = 3,
        flip_x: bool = True,
    ):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.margin_center = margin_center
        self.margin_edge = margin_edge
        self.blend_zone = blend_zone
        self.dead_zone = dead_zone
        self.flip_x = flip_x
        self._last_x: int = screen_w // 2
        self._last_y: int = screen_h // 2

    def _edge_proximity(self, norm_x: float, norm_y: float) -> float:
        """Cubic smoothstep edge proximity factor (0=center, 1=edge)."""
        min_dist = min(norm_x, 1.0 - norm_x, norm_y, 1.0 - norm_y)
        if min_dist >= self.blend_zone:
            return 0.0
        t = 1.0 - (min_dist / self.blend_zone)
        return t * t * (3.0 - 2.0 * t)

    def map_to_screen(
        self,
        norm_x: float,
        norm_y: float,
        apply_dead_zone: bool = True,
    ) -> Tuple[int, int]:
        """Map normalized (0-1) hand coordinates to screen pixels.

        Args:
            norm_x: Normalized X (0=left, 1=right in camera frame).
            norm_y: Normalized Y (0=top, 1=bottom).
            apply_dead_zone: Whether to apply dead zone filtering.

        Returns:
            (x, y) screen pixel coordinates.
        """
        # Mirror X for natural cursor control (webcam is mirrored)
        if self.flip_x:
            norm_x = 1.0 - norm_x

        # Clamp to valid range
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        # Edge-aware margin adjustment
        edge_factor = self._edge_proximity(norm_x, norm_y)
        margin = self.margin_center * (1.0 - edge_factor) + self.margin_edge * edge_factor

        # Apply margin mapping
        mapped_x = max(0.0, min(1.0, (norm_x - margin) / (1.0 - 2.0 * margin)))
        mapped_y = max(0.0, min(1.0, (norm_y - margin) / (1.0 - 2.0 * margin)))

        # Convert to screen coordinates
        sx = int(max(0, min(self.screen_w - 1, mapped_x * self.screen_w)))
        sy = int(max(0, min(self.screen_h - 1, mapped_y * self.screen_h)))

        # Apply dead zone
        if apply_dead_zone and self.dead_zone > 0:
            dx = sx - self._last_x
            dy = sy - self._last_y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < self.dead_zone:
                return (self._last_x, self._last_y)

        self._last_x = sx
        self._last_y = sy
        return (sx, sy)

    def reset(self) -> None:
        """Reset last position to screen center."""
        self._last_x = self.screen_w // 2
        self._last_y = self.screen_h // 2
