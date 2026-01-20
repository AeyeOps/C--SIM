"""
Histogram statistics classes.

Port of C++SIM Stat/Histogram.cc and Stat/PrecisionHistogram.cc.

Class hierarchy matches C++:
  Histogram -> PrecisionHistogram -> Variance -> Mean
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from pysim.stats.variance import Variance


class MergeChoice(Enum):
    """Merge policy when histogram reaches capacity."""

    ACCUMULATE = auto()  # Combine counts, keep higher bucket name
    MEAN = auto()  # Weighted average of names, combine counts
    MAX = auto()  # Keep higher bucket name and its count only
    MIN = auto()  # Keep lower bucket name and its count only


@dataclass
class Bucket:
    """A single histogram bucket."""

    name: float  # Bucket center/value
    count: int = 0  # Number of entries

    @property
    def size(self) -> int:
        """Alias for count (C++ uses 'size')."""
        return self.count


class PrecisionHistogram(Variance):
    """
    Unbounded precision histogram.

    Maintains exact counts for each unique value seen.
    Buckets are stored in sorted order by name.

    Inherits from Variance to track statistical moments alongside
    bucket counts, matching C++ class hierarchy.

    From Stat/src/PrecisionHistogram.cc.
    """

    def __init__(self) -> None:
        super().__init__()
        self._buckets: list[Bucket] = []

    def reset(self) -> None:
        """Clear all buckets and reset statistics."""
        self._buckets = []
        super().reset()

    @property
    def number_of_buckets(self) -> int:
        """Number of distinct values tracked."""
        return len(self._buckets)

    @property
    def total_entries(self) -> int:
        """Total number of samples."""
        return sum(b.count for b in self._buckets)

    def is_present(self, value: float) -> bool:
        """Check if value already has a bucket."""
        for b in self._buckets:
            if b.name == value:
                return True
        return False

    def create(self, value: float) -> None:
        """
        Create an empty bucket for the given value if not present.

        Used by SimpleHistogram to pre-create buckets.
        From PHistogram.cc:99-113.
        """
        if self.is_present(value):
            return

        # Insert new bucket in sorted order with count=0
        new_bucket = Bucket(name=value, count=0)
        for i, b in enumerate(self._buckets):
            if b.name > value:
                self._buckets.insert(i, new_bucket)
                return
        self._buckets.append(new_bucket)

    def set_value(self, value: float) -> None:
        """
        Add a sample value.

        Updates Variance statistics AND creates/increments bucket count.
        From PHistogram.cc:195-215.
        """
        # Update variance statistics (calls Mean.set_value internally)
        super().set_value(value)

        # Check if bucket exists
        for b in self._buckets:
            if b.name == value:
                b.count += 1
                return

        # Insert new bucket in sorted order
        new_bucket = Bucket(name=value, count=1)
        for i, b in enumerate(self._buckets):
            if b.name > value:
                self._buckets.insert(i, new_bucket)
                return
        self._buckets.append(new_bucket)

    def __iadd__(self, value: float) -> PrecisionHistogram:
        """Operator += equivalent."""
        self.set_value(value)
        return self

    def size_by_name(self, name: float) -> int | None:
        """Get bucket count by name, or None if not present."""
        for b in self._buckets:
            if b.name == name:
                return b.count
            if b.name > name:
                break
        return None

    def size_by_index(self, index: int) -> int | None:
        """Get bucket count by index, or None if invalid."""
        if 0 <= index < len(self._buckets):
            return self._buckets[index].count
        return None

    def bucket_name(self, index: int) -> float | None:
        """Get bucket name by index, or None if invalid."""
        if 0 <= index < len(self._buckets):
            return self._buckets[index].name
        return None

    def save_state(self, path: Path | str) -> bool:
        """Serialize state to file."""
        try:
            with open(path, "w") as f:
                f.write(f" {len(self._buckets)}")
                for b in self._buckets:
                    f.write(f" {b.name} {b.count}")
                # Variance state (includes Mean state)
                f.write(f" {self._sum_sq}")
                f.write(f" {self._max} {self._min}")
                f.write(f" {self._sum} {self._mean}")
                f.write(f" {self._number} ")
            return True
        except IOError:
            return False

    def restore_state(self, path: Path | str) -> bool:
        """Restore state from file."""
        try:
            with open(path) as f:
                parts = f.read().split()
                idx = 0
                n = int(parts[idx])
                idx += 1
                self._buckets = []
                for _ in range(n):
                    name = float(parts[idx])
                    count = int(parts[idx + 1])
                    self._buckets.append(Bucket(name=name, count=count))
                    idx += 2
                # Variance state
                self._sum_sq = float(parts[idx])
                idx += 1
                self._max = float(parts[idx])
                self._min = float(parts[idx + 1])
                self._sum = float(parts[idx + 2])
                self._mean = float(parts[idx + 3])
                self._number = int(parts[idx + 4])
            return True
        except (IOError, IndexError, ValueError):
            return False

    def __str__(self) -> str:
        """
        String representation matching C++ output.

        Format: Buckets first, then Variance stats, then Mean stats.
        From PHistogram.cc:217-227.
        """
        lines = []
        if len(self._buckets) == 0:
            lines.append("Empty histogram")
        else:
            for b in self._buckets:
                lines.append(f"Bucket : < {b.name}, {b.count} >")

        # Variance section (includes Mean via super().__str__)
        lines.append(super().__str__())
        return "\n".join(lines)


class Histogram(PrecisionHistogram):
    """
    Fixed-capacity histogram with merge policies.

    When capacity is reached and a new unique value arrives,
    adjacent bucket pairs are merged according to the merge policy.

    From Stat/src/Histogram.cc.
    """

    def __init__(self, max_buckets: int = 100, merge: MergeChoice = MergeChoice.MEAN) -> None:
        super().__init__()
        self._max_size = max(2, max_buckets)
        self._merge = merge

    def _composite_name(self, a: Bucket, b: Bucket) -> float:
        """
        Compute merged bucket name.

        Buckets are in sorted order, so a.name < b.name.
        From Histogram.cc:58-74.
        """
        match self._merge:
            case MergeChoice.ACCUMULATE | MergeChoice.MAX:
                return b.name
            case MergeChoice.MEAN:
                total = a.size + b.size
                if total == 0:
                    return (a.name + b.name) / 2
                return (a.name * a.size + b.name * b.size) / total
            case MergeChoice.MIN:
                return a.name
        return 0.0  # Should not reach

    def _composite_size(self, a: Bucket, b: Bucket) -> int:
        """
        Compute merged bucket size.

        From Histogram.cc:76-96.
        """
        match self._merge:
            case MergeChoice.ACCUMULATE | MergeChoice.MEAN:
                return a.size + b.size
            case MergeChoice.MAX:
                return b.size
            case MergeChoice.MIN:
                return a.size
        return 0  # Should not reach

    def _merge_buckets(self) -> None:
        """
        Merge adjacent bucket pairs to reduce count.

        From Histogram.cc:98-145.
        """
        new_buckets: list[Bucket] = []
        i = 0

        while i < len(self._buckets):
            if i + 1 < len(self._buckets):
                # Merge pair
                a, b = self._buckets[i], self._buckets[i + 1]
                merged = Bucket(
                    name=self._composite_name(a, b),
                    count=self._composite_size(a, b),
                )
                new_buckets.append(merged)
                i += 2
            else:
                # Odd bucket, keep as-is
                new_buckets.append(self._buckets[i])
                i += 1

        self._buckets = new_buckets

    def set_value(self, value: float) -> None:
        """
        Add a sample value.

        Triggers merge if at capacity and value is new.
        From Histogram.cc:147-153.
        """
        if self.number_of_buckets == self._max_size and not self.is_present(value):
            self._merge_buckets()

        super().set_value(value)

    def save_state(self, path: Path | str) -> bool:
        """Serialize state to file."""
        try:
            with open(path, "w") as f:
                f.write(f" {self._max_size} {self._merge.value}")
            # Append parent state
            with open(path, "a") as f:
                f.write(f" {len(self._buckets)}")
                for b in self._buckets:
                    f.write(f" {b.name} {b.count}")
                # Variance state
                f.write(f" {self._sum_sq}")
                f.write(f" {self._max} {self._min}")
                f.write(f" {self._sum} {self._mean}")
                f.write(f" {self._number} ")
            return True
        except IOError:
            return False

    def restore_state(self, path: Path | str) -> bool:
        """Restore state from file."""
        try:
            with open(path) as f:
                parts = f.read().split()
                self._max_size = int(parts[0])
                self._merge = MergeChoice(int(parts[1]))
                idx = 2
                n = int(parts[idx])
                idx += 1
                self._buckets = []
                for _ in range(n):
                    name = float(parts[idx])
                    count = int(parts[idx + 1])
                    self._buckets.append(Bucket(name=name, count=count))
                    idx += 2
                # Variance state
                self._sum_sq = float(parts[idx])
                idx += 1
                self._max = float(parts[idx])
                self._min = float(parts[idx + 1])
                self._sum = float(parts[idx + 2])
                self._mean = float(parts[idx + 3])
                self._number = int(parts[idx + 4])
            return True
        except (IOError, IndexError, ValueError):
            return False

    def __str__(self) -> str:
        """String representation matching C++ output."""
        merge_names = {
            MergeChoice.ACCUMULATE: "ACCUMULATE",
            MergeChoice.MEAN: "MEAN",
            MergeChoice.MAX: "MAX",
            MergeChoice.MIN: "MIN",
        }
        lines = [
            f"Maximum number of buckets {self._max_size}",
            f"Merge choice is {merge_names[self._merge]}",
        ]
        # Parent str() includes buckets + variance + mean
        lines.append(super().__str__())
        return "\n".join(lines)
