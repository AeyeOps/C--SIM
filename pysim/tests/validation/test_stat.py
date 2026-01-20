"""
Validation test for Tests/Stat (histogram tests).

Compares Python output against C++SIM Tests/Stat/expected_output.

Tests PrecisionHistogram, Histogram, SimpleHistogram, and Quantile
with ExponentialStream(10) input for 100 and 200 samples.
"""

import pytest

from pysim.random import ExponentialStream, reset_prng_cache
from pysim.stats import PrecisionHistogram, Histogram, SimpleHistogram, Quantile


class TestStatHistograms:
    """Test replication of Tests/Stat histogram output."""

    def setup_method(self) -> None:
        """Reset state for deterministic tests."""
        reset_prng_cache()

    def test_precision_histogram_100_samples(self) -> None:
        """
        PrecisionHistogram with 100 ExponentialStream(10) samples.

        Expected:
            Number of samples : 100
            Variance          : 120.217
            Mean              : 10.6125
            Sum               : 1061.25
        """
        reset_prng_cache()
        stream = ExponentialStream(10)
        hist = PrecisionHistogram()

        for _ in range(100):
            hist += stream()

        assert hist.number_of_samples == 100
        assert hist.number_of_buckets == 100  # All unique values
        assert abs(hist.variance - 120.217) < 0.01, f"Got {hist.variance}"
        assert abs(hist.mean - 10.6125) < 0.001, f"Got {hist.mean}"
        assert abs(hist.sum - 1061.25) < 0.01, f"Got {hist.sum}"

    def test_precision_histogram_200_samples(self) -> None:
        """
        PrecisionHistogram with 200 samples (100 + 100 more with same values).

        The C++ test runs 100 samples, saves, then loads and runs 100 more.
        Our Python implementation increments count for duplicate values
        rather than creating new bucket entries (different from C++).

        Key validation: statistics should match.
        Expected:
            Number of samples : 200
            Variance          : 119.613
            Mean              : 10.6125
        """
        reset_prng_cache()
        stream = ExponentialStream(10)
        hist = PrecisionHistogram()

        # First 100 samples
        for _ in range(100):
            hist += stream()

        # Reset and add same 100 again (simulates C++ save/load pattern)
        reset_prng_cache()
        stream2 = ExponentialStream(10)
        for _ in range(100):
            hist += stream2()

        assert hist.number_of_samples == 200
        # Python merges duplicates: 100 unique values with count=2 each
        assert hist.number_of_buckets == 100
        assert abs(hist.variance - 119.613) < 0.01, f"Got {hist.variance}"
        assert abs(hist.mean - 10.6125) < 0.001, f"Got {hist.mean}"

    def test_histogram_100_samples_merge(self) -> None:
        """
        Histogram with 20 buckets, 100 samples, MEAN merge policy.

        Expected:
            Number of samples : 100
            Variance          : 120.217
            Mean              : 10.6125
            20 buckets (after merging)
        """
        reset_prng_cache()
        stream = ExponentialStream(10)
        hist = Histogram(max_buckets=20)

        for _ in range(100):
            hist += stream()

        assert hist.number_of_samples == 100
        assert hist.number_of_buckets == 20  # Merged to max
        assert abs(hist.variance - 120.217) < 0.01, f"Got {hist.variance}"
        assert abs(hist.mean - 10.6125) < 0.001, f"Got {hist.mean}"

    def test_simple_histogram_100_samples(self) -> None:
        """
        SimpleHistogram with fixed range [0, 55), 20 buckets.

        Expected:
            Number of buckets    : 20
            width of each bucket : 2.75
            Number of samples : 100
            Variance          : 118.045 (different due to bucket center approximation)
        """
        reset_prng_cache()
        stream = ExponentialStream(10)
        hist = SimpleHistogram(min_val=0.0, max_val=55.0, nbuckets=20)

        for _ in range(100):
            hist += stream()

        assert hist.number_of_samples == 100
        assert hist.number_of_buckets == 20
        assert abs(hist.width - 2.75) < 0.01, f"Got width {hist.width}"
        # SimpleHistogram uses bucket centers, so statistics differ slightly
        assert abs(hist.variance - 118.045) < 0.1, f"Got {hist.variance}"
        assert abs(hist.mean - 9.2675) < 0.01, f"Got {hist.mean}"

    def test_quantile_100_samples(self) -> None:
        """
        Quantile (95th percentile) with 100 samples.

        Expected:
            Quantile precentage : 0.95
            Value below which percentage occurs 35.2073
            Number of samples : 100
            Variance          : 120.217
        """
        reset_prng_cache()
        stream = ExponentialStream(10)
        hist = Quantile(0.95)

        for _ in range(100):
            hist += stream()

        assert hist.number_of_samples == 100
        assert abs(hist() - 35.2073) < 0.001, f"Got {hist()}"
        assert abs(hist.variance - 120.217) < 0.01, f"Got {hist.variance}"
        assert abs(hist.mean - 10.6125) < 0.001, f"Got {hist.mean}"

    def test_quantile_200_samples(self) -> None:
        """
        Quantile with 200 samples.

        Expected:
            Quantile precentage : 0.95
            Value below which percentage occurs 35.2073
            Number of samples : 200
        """
        reset_prng_cache()
        stream = ExponentialStream(10)
        hist = Quantile(0.95)

        # First 100 samples
        for _ in range(100):
            hist += stream()

        # Reset and add same 100 again
        reset_prng_cache()
        stream2 = ExponentialStream(10)
        for _ in range(100):
            hist += stream2()

        assert hist.number_of_samples == 200
        # 95th percentile of 200 samples is at position 190
        assert abs(hist() - 35.2073) < 0.001, f"Got {hist()}"

    def test_first_bucket_value(self) -> None:
        """Verify first bucket matches expected output exactly."""
        reset_prng_cache()
        stream = ExponentialStream(10)
        hist = PrecisionHistogram()

        for _ in range(100):
            hist += stream()

        # First bucket should be the minimum value
        first_name = hist.bucket_name(0)
        assert first_name is not None
        assert abs(first_name - 0.0546439) < 0.0001, f"Got {first_name}"

    def test_last_bucket_value(self) -> None:
        """Verify last bucket matches expected output exactly."""
        reset_prng_cache()
        stream = ExponentialStream(10)
        hist = PrecisionHistogram()

        for _ in range(100):
            hist += stream()

        # Last bucket should be the maximum value
        last_name = hist.bucket_name(hist.number_of_buckets - 1)
        assert last_name is not None
        assert abs(last_name - 47.6499) < 0.001, f"Got {last_name}"
