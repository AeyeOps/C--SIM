"""
SimpleHistogram - fixed-width bucket histogram.

Port of C++SIM Stat/SHistogram.cc.
"""

from __future__ import annotations

import sys
from pathlib import Path

from pysim.stats.histogram import Bucket, PrecisionHistogram
from pysim.stats.variance import Variance


class SimpleHistogram(PrecisionHistogram):
    """
    Histogram with fixed-width buckets over a defined range.

    Unlike PrecisionHistogram which creates buckets on demand,
    SimpleHistogram pre-creates buckets at initialization and
    rejects values outside the [min, max] range.

    From Stat/src/SHistogram.cc.
    """

    def __init__(
        self,
        min_val: float,
        max_val: float,
        nbuckets: int | None = None,
        width: float | None = None,
    ) -> None:
        """
        Create histogram with fixed-width buckets.

        Args:
            min_val: Minimum value (lower bound)
            max_val: Maximum value (upper bound)
            nbuckets: Number of buckets (if provided, width is computed)
            width: Bucket width (if provided, nbuckets is computed)

        Must provide exactly one of nbuckets or width.
        """
        # Set instance attributes BEFORE calling super().__init__()
        # because Mean.__init__() calls reset() which needs these
        # Ensure min < max (C++ swaps if needed)
        self._min_index = min(min_val, max_val)
        self._max_index = max(min_val, max_val)

        if nbuckets is not None and width is None:
            # Compute width from number of buckets
            self._number_buckets = max(1, nbuckets)
            self._width = (self._max_index - self._min_index) / self._number_buckets
        elif width is not None and nbuckets is None:
            # Compute number of buckets from width
            self._width = width if width > 0 else 2.0
            n = (self._max_index - self._min_index) / self._width
            # C++ rounds up if there's a fractional part
            self._number_buckets = int(n) if n == int(n) else int(n) + 1
        else:
            raise ValueError("Must provide exactly one of nbuckets or width")

        super().__init__()
        self._create_buckets()

    def _create_buckets(self) -> None:
        """Pre-create all buckets with fixed width."""
        self._buckets = []
        value = self._min_index
        for _ in range(self._number_buckets):
            self._buckets.append(Bucket(name=value, count=0))
            value += self._width

    def reset(self) -> None:
        """Reset histogram: re-create empty buckets and reset statistics."""
        # Call parent reset first to initialize Mean/Variance stats
        super().reset()
        # Then recreate our fixed-width buckets
        self._create_buckets()

    @property
    def width(self) -> float:
        """Bucket width."""
        return self._width

    @property
    def min_index(self) -> float:
        """Minimum range value."""
        return self._min_index

    @property
    def max_index(self) -> float:
        """Maximum range value."""
        return self._max_index

    def size_by_name(self, name: float) -> int | None:
        """
        Get bucket count for a value.

        Returns None if value outside range.
        From SHistogram.cc:84-101.
        """
        if name < self._min_index or name > self._max_index:
            return None

        for bucket in self._buckets:
            bucket_value = bucket.name
            if name == bucket_value or name <= bucket_value + self._width:
                return bucket.count

        return None

    def set_value(self, value: float) -> None:
        """
        Add a sample value.

        Values outside [min, max] are rejected with a warning.
        From SHistogram.cc:103-130.
        """
        if value < self._min_index or value > self._max_index:
            print(
                f"Value {value} is beyond histogram range "
                f"[ {self._min_index}, {self._max_index} ]",
                file=sys.stderr,
            )
            return

        for bucket in self._buckets:
            bucket_value = bucket.name
            if value == bucket_value or value <= bucket_value + self._width:
                # Update Variance stats (bypassing PrecisionHistogram bucket creation)
                Variance.set_value(self, bucket_value)
                bucket.count += 1
                return

        # Should not reach here
        print(
            f"SimpleHistogram.set_value - Something went wrong with {value}",
            file=sys.stderr,
        )

    def save_state(self, path: Path | str) -> bool:
        """Serialize state to file."""
        try:
            with open(path, "w") as f:
                f.write(f"{self._min_index} {self._max_index} ")
                f.write(f"{self._width} {self._number_buckets} ")
                # Parent state
                f.write(f"{len(self._buckets)} ")
                for b in self._buckets:
                    f.write(f"{b.name} {b.count} ")
            return True
        except IOError:
            return False

    def restore_state(self, path: Path | str) -> bool:
        """Restore state from file."""
        try:
            with open(path) as f:
                parts = f.read().split()
                self._min_index = float(parts[0])
                self._max_index = float(parts[1])
                self._width = float(parts[2])
                self._number_buckets = int(parts[3])
                n = int(parts[4])
                self._buckets = []
                for i in range(n):
                    name = float(parts[5 + i * 2])
                    count = int(parts[6 + i * 2])
                    self._buckets.append(Bucket(name=name, count=count))
            return True
        except (IOError, IndexError, ValueError):
            return False

    def __str__(self) -> str:
        """String representation matching C++ output."""
        lines = [
            f"Maximum index range  : {self._max_index}",
            f"Minimum index range  : {self._min_index}",
            f"Number of buckets    : {self._number_buckets}",
            f"width of each bucket : {self._width}",
        ]
        lines.append(super().__str__())
        return "\n".join(lines)
