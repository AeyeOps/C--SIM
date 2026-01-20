"""
Variance statistics class.

Port of C++SIM Stat/Variance.cc.
"""

from __future__ import annotations

import math
from pathlib import Path

from pysim.stats.mean import Mean


class Variance(Mean):
    """
    Running variance calculation.

    Extends Mean with variance, standard deviation, and confidence interval.

    From Stat/src/Variance.cc.
    """

    def __init__(self) -> None:
        super().__init__()
        self._sum_sq: float = 0.0

    def reset(self) -> None:
        """Reset all statistics."""
        super().reset()
        self._sum_sq = 0.0

    def set_value(self, value: float) -> None:
        """Add a sample value."""
        super().set_value(value)
        self._sum_sq += value * value

    @property
    def variance(self) -> float:
        """
        Sample variance.

        Uses n-1 denominator (Bessel's correction).
        """
        if self._number < 2:
            return 0.0
        return (self._sum_sq - (self._sum * self._sum) / self._number) / (self._number - 1)

    @property
    def std_dev(self) -> float:
        """Sample standard deviation."""
        return math.sqrt(self.variance)

    def confidence(self, percent: float = 95.0) -> float:
        """
        Confidence interval half-width.

        Uses t-distribution approximation for large samples.
        For 95% confidence with large n, t ≈ 1.96.
        """
        if self._number < 2:
            return 0.0

        # t-values for common confidence levels (large sample approximation)
        t_values = {
            90.0: 1.645,
            95.0: 1.960,
            99.0: 2.576,
        }
        t = t_values.get(percent, 1.960)

        return t * self.std_dev / math.sqrt(self._number)

    def save_state(self, path: Path | str) -> bool:
        """Serialize state to file."""
        if not super().save_state(path):
            return False
        try:
            with open(path, "a") as f:
                f.write(f" {self._sum_sq} ")
            return True
        except IOError:
            return False

    def restore_state(self, path: Path | str) -> bool:
        """Restore state from file."""
        if not super().restore_state(path):
            return False
        try:
            with open(path) as f:
                parts = f.read().split()
                if len(parts) > 5:
                    self._sum_sq = float(parts[5])
            return True
        except (IOError, IndexError, ValueError):
            return False

    def __str__(self) -> str:
        """
        String representation matching C++ output.

        C++ prints Variance/StdDev first, then Mean stats.
        From Variance.cc:131-137.
        """
        lines = [
            f"Variance          : {self.variance}",
            f"Standard Deviation: {self.std_dev}",
        ]
        # Mean stats follow
        lines.append(super().__str__())
        return "\n".join(lines)
