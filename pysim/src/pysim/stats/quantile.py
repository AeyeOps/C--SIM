"""
Quantile estimation class.

Port of C++SIM Stat/Quantile.cc - inherits from PrecisionHistogram.
"""

from __future__ import annotations

import sys

from pysim.stats.histogram import PrecisionHistogram


class Quantile(PrecisionHistogram):
    """
    Quantile calculation using PrecisionHistogram bucket traversal.

    Stores all values in sorted buckets and computes quantile by
    walking through buckets until the cumulative count reaches
    the target percentage.

    From Stat/src/Quantile.cc.
    """

    def __init__(self, q: float = 0.95) -> None:
        """
        Initialize for q-quantile estimation.

        Args:
            q: The quantile to estimate (0.5 = median, 0.95 = 95th percentile).
               Must be in range (0, 1]. Defaults to 0.95.
        """
        super().__init__()
        if q <= 0.0 or q > 1.0:
            print(f"Quantile::Quantile ( {q} ) : bad value.", file=sys.stderr)
            self._q_prob = 0.95
        else:
            self._q_prob = q

    def __call__(self) -> float:
        """
        Return the quantile value.

        Walks through sorted buckets, accumulating counts until
        reaching the target percentage of samples.

        From Quantile.cc:45-65.
        """
        p_samples = self.number_of_samples * self._q_prob
        n_entries = 0
        trail_name = 0.0

        if p_samples == 0.0:
            print("Quantile::operator() : percentage samples error.", file=sys.stderr)
            return 0.0

        for bucket in self._buckets:
            n_entries += bucket.count
            trail_name = bucket.name
            if n_entries >= p_samples:
                break

        return trail_name

    @property
    def value(self) -> float:
        """Alias for __call__ to match P^2 API."""
        return self()

    def range(self) -> float:
        """
        Return the range (max - min) of observed values.

        From Quantile.n inline.
        """
        return self._max - self._min

    def __str__(self) -> str:
        """
        String representation matching C++ output.

        Format: Quantile percentage + value, then PrecisionHistogram output.
        From Quantile.cc:67-72.
        """
        lines = [
            f"Quantile precentage : {self._q_prob}",
            f"Value below which percentage occurs {self()}",
            super().__str__(),
        ]
        return "\n".join(lines)
