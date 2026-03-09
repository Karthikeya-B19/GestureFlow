"""Smoothing filters for gesture coordinate data.

Includes EMA, adaptive velocity-responsive smoother, and One-Euro filter.
"""

import math
import time
from typing import Optional, Tuple


class ExponentialMovingAverage:
    """Simple exponential moving average filter.

    Args:
        alpha: Smoothing factor in [0, 1]. Higher = less smoothing.
    """

    def __init__(self, alpha: float = 0.5):
        self.alpha = max(0.0, min(1.0, alpha))
        self._value: Optional[float] = None

    def update(self, value: float) -> float:
        """Update with new value, return smoothed result."""
        if self._value is None:
            self._value = value
        else:
            self._value = self.alpha * value + (1.0 - self.alpha) * self._value
        return self._value

    def reset(self) -> None:
        """Reset filter state."""
        self._value = None

    @property
    def value(self) -> Optional[float]:
        return self._value


class CoordinateSmoother:
    """2D coordinate smoother using two independent EMA filters.

    Args:
        alpha: Smoothing factor for both axes.
    """

    def __init__(self, alpha: float = 0.5):
        self._x_filter = ExponentialMovingAverage(alpha)
        self._y_filter = ExponentialMovingAverage(alpha)

    def update(self, x: float, y: float) -> Tuple[float, float]:
        """Update with new coordinates, return smoothed (x, y)."""
        sx = self._x_filter.update(x)
        sy = self._y_filter.update(y)
        return (sx, sy)

    def reset(self) -> None:
        """Reset both axis filters."""
        self._x_filter.reset()
        self._y_filter.reset()


class AdaptiveCoordinateSmoother:
    """Velocity-responsive coordinate smoother.

    Adjusts smoothing based on hand movement speed:
    - Fast movement: higher alpha (responsive, less smoothing)
    - Slow movement: lower alpha (smooth, less jitter)

    Args:
        alpha_slow: Alpha when hand is stationary (heavy smoothing).
        alpha_fast: Alpha when hand is moving fast (light smoothing).
        velocity_threshold: Speed (px/frame) above which full fast alpha is used.
    """

    def __init__(
        self,
        alpha_slow: float = 0.2,
        alpha_fast: float = 0.8,
        velocity_threshold: float = 50.0,
    ):
        self.alpha_slow = alpha_slow
        self.alpha_fast = alpha_fast
        self.velocity_threshold = velocity_threshold
        self._prev_x: Optional[float] = None
        self._prev_y: Optional[float] = None
        self._smooth_x: Optional[float] = None
        self._smooth_y: Optional[float] = None

    def update(self, x: float, y: float) -> Tuple[float, float]:
        """Update with raw coordinates, return adaptively smoothed (x, y)."""
        if self._prev_x is None:
            self._prev_x = x
            self._prev_y = y
            self._smooth_x = x
            self._smooth_y = y
            return (x, y)

        # Calculate velocity (pixel distance between frames)
        dx = x - self._prev_x
        dy = y - self._prev_y
        velocity = math.sqrt(dx * dx + dy * dy)

        # Interpolate alpha based on velocity
        t = min(1.0, velocity / self.velocity_threshold)
        alpha = self.alpha_slow + t * (self.alpha_fast - self.alpha_slow)

        # Apply EMA with adaptive alpha
        self._smooth_x = alpha * x + (1.0 - alpha) * self._smooth_x
        self._smooth_y = alpha * y + (1.0 - alpha) * self._smooth_y

        self._prev_x = x
        self._prev_y = y

        return (self._smooth_x, self._smooth_y)

    def reset(self) -> None:
        """Reset filter state."""
        self._prev_x = None
        self._prev_y = None
        self._smooth_x = None
        self._smooth_y = None


class OneEuroFilter:
    """One-Euro filter for low-latency, low-jitter signal smoothing.

    Superior to EMA for cursor control — adapts cutoff frequency to signal speed.

    Args:
        min_cutoff: Minimum cutoff frequency (lower = more smoothing at rest).
        beta: Speed coefficient (higher = less lag during fast movement).
        d_cutoff: Cutoff frequency for derivative filtering.
    """

    def __init__(
        self,
        min_cutoff: float = 1.0,
        beta: float = 0.007,
        d_cutoff: float = 1.0,
    ):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x_prev: Optional[float] = None
        self._dx_prev: float = 0.0
        self._t_prev: Optional[float] = None

    @staticmethod
    def _smoothing_factor(t_e: float, cutoff: float) -> float:
        r = 2.0 * math.pi * cutoff * t_e
        return r / (r + 1.0)

    def update(self, x: float, t: Optional[float] = None) -> float:
        """Filter a single value. Optionally pass timestamp (seconds)."""
        if t is None:
            t = time.time()

        if self._t_prev is None:
            self._x_prev = x
            self._dx_prev = 0.0
            self._t_prev = t
            return x

        t_e = t - self._t_prev
        if t_e <= 0:
            t_e = 1.0 / 30.0  # Assume 30fps if zero delta

        # Filter derivative
        a_d = self._smoothing_factor(t_e, self.d_cutoff)
        dx = (x - self._x_prev) / t_e
        dx_hat = a_d * dx + (1.0 - a_d) * self._dx_prev

        # Adaptive cutoff
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)

        # Filter signal
        a = self._smoothing_factor(t_e, cutoff)
        x_hat = a * x + (1.0 - a) * self._x_prev

        self._x_prev = x_hat
        self._dx_prev = dx_hat
        self._t_prev = t

        return x_hat

    def reset(self) -> None:
        """Reset filter state."""
        self._x_prev = None
        self._dx_prev = 0.0
        self._t_prev = None


class OneEuroFilter2D:
    """2D One-Euro filter for cursor coordinates.

    Args:
        min_cutoff: Minimum cutoff frequency.
        beta: Speed coefficient.
        d_cutoff: Derivative cutoff frequency.
    """

    def __init__(
        self,
        min_cutoff: float = 1.0,
        beta: float = 0.007,
        d_cutoff: float = 1.0,
    ):
        self._x_filter = OneEuroFilter(min_cutoff, beta, d_cutoff)
        self._y_filter = OneEuroFilter(min_cutoff, beta, d_cutoff)

    def update(self, x: float, y: float, t: Optional[float] = None) -> Tuple[float, float]:
        """Filter 2D coordinates."""
        sx = self._x_filter.update(x, t)
        sy = self._y_filter.update(y, t)
        return (sx, sy)

    def reset(self) -> None:
        """Reset both axis filters."""
        self._x_filter.reset()
        self._y_filter.reset()
