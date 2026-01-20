"""
Time-weighted variance class.

Port of C++SIM Stat/TimeVariance.cc.
"""

from __future__ import annotations

from pysim.stats.variance import Variance


class TimeVariance(Variance):
    """
    Time-weighted variance calculation.

    Tracks area under the curve for time-weighted statistics.
    Each value is weighted by the time it was held.

    From Stat/src/TimeVariance.cc.
    """

    def __init__(self) -> None:
        super().__init__()
        self._current_value: float = 0.0
        self._stime: float = 0.0  # Start time of current value

    def reset(self) -> None:
        """Reset all statistics."""
        super().reset()
        self._current_value = 0.0
        self._stime = 0.0

    @staticmethod
    def _current_time() -> float:
        """Get current simulation time."""
        from pysim.process import Process

        return Process.current_time()

    @property
    def area(self) -> float:
        """
        Area under curve since last set_value.

        From TimeVariance.n:50-53.
        """
        return self._current_value * (self._current_time() - self._stime)

    @property
    def current_value(self) -> float:
        """Current value being tracked."""
        return self._current_value

    def set_value(self, value: float) -> None:
        """
        Record new value, updating time-weighted statistics.

        The area for the previous value (value * duration) is
        added to the statistics before switching to the new value.
        """
        # Add area for previous value
        super().set_value(self.area)

        # Start tracking new value
        self._current_value = value
        self._stime = self._current_time()

    def finalize(self) -> None:
        """
        Finalize statistics by recording final area.

        Call this at end of simulation to include the last value's contribution.
        """
        super().set_value(self.area)
        self._stime = self._current_time()

    def __str__(self) -> str:
        """String representation."""
        base = super().__str__()
        extra = [
            f"Current value     : {self._current_value}",
            f"Current area      : {self.area}",
        ]
        return base + "\n" + "\n".join(extra)
