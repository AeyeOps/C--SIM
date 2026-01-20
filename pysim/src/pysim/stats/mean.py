"""
Mean statistics class.

Port of C++SIM Stat/Mean.cc.
"""

from __future__ import annotations

from pathlib import Path

# C++ 32-bit float limits (for bug-compatible output)
# C++ numeric_limits<float>::max() = 3.40282e+38
# C++ numeric_limits<float>::min() = 1.17549e-38 (smallest positive, NOT negative!)
CPP_FLOAT_MAX = 3.40282346638528859812e+38
CPP_FLOAT_MIN = 1.17549435082228750797e-38


class Mean:
    """
    Running mean calculation.

    From Stat/src/Mean.cc.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """
        Reset all statistics.

        Note: C++ uses numeric_limits<float>::min() for _Min, which returns
        the smallest POSITIVE float (~1.17e-38), NOT negative infinity.
        This is a C++ bug (should use lowest()), but we replicate it exactly
        to match expected_output files.

        Similarly, _Max is initialized to numeric_limits<float>::max() (~3.4e+38).

        From Mean.cc:46-54.
        """
        # Bug-compatible: C++ initializes to float limits
        # _Max = numeric_limits<float>::max() means new values are always < _Max
        # _Min = numeric_limits<float>::min() (smallest positive!) means new values > _Min
        # Result: min/max never get updated properly in C++ - this is a bug we replicate
        self._max: float = CPP_FLOAT_MAX
        self._min: float = CPP_FLOAT_MIN
        self._sum: float = 0.0
        self._mean: float = 0.0
        self._number: int = 0

    def set_value(self, value: float) -> None:
        """
        Add a sample value.

        From Mean.cc:56-65.
        """
        if value > self._max:
            self._max = value
        if value < self._min:
            self._min = value
        self._sum += value
        self._number += 1
        self._mean = self._sum / self._number

    def __iadd__(self, value: float) -> Mean:
        """Operator += equivalent."""
        self.set_value(value)
        return self

    @property
    def number_of_samples(self) -> int:
        """Number of samples collected."""
        return self._number

    @property
    def min(self) -> float:
        """Minimum value seen."""
        return self._min

    @property
    def max(self) -> float:
        """Maximum value seen."""
        return self._max

    @property
    def sum(self) -> float:
        """Sum of all values."""
        return self._sum

    @property
    def mean(self) -> float:
        """Current mean value."""
        return self._mean

    def save_state(self, path: Path | str) -> bool:
        """
        Serialize state to file.

        From Mean.cc:67-92.
        """
        try:
            with open(path, "w") as f:
                f.write(f" {self._max} {self._min}")
                f.write(f" {self._sum} {self._mean}")
                f.write(f" {self._number} ")
            return True
        except IOError:
            return False

    def restore_state(self, path: Path | str) -> bool:
        """
        Restore state from file.

        From Mean.cc:94-119.
        """
        try:
            with open(path) as f:
                parts = f.read().split()
                self._max = float(parts[0])
                self._min = float(parts[1])
                self._sum = float(parts[2])
                self._mean = float(parts[3])
                self._number = int(parts[4])
            return True
        except (IOError, IndexError, ValueError):
            return False

    def __str__(self) -> str:
        """
        String representation matching C++ output.

        From Mean.cc:121-130.
        """
        lines = [
            f"Number of samples : {self.number_of_samples}",
            f"Minimum           : {self.min}",
            f"Maximum           : {self.max}",
            f"Sum               : {self.sum}",
            f"Mean              : {self.mean}",
        ]
        return "\n".join(lines)
