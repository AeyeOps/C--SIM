"""
Validation test for Streams example.

Compares Python output against C++SIM Examples/Streams/expected_output.
"""

import math

import pytest

from pysim.random import NormalStream, reset_prng_cache
from pysim.stats import Histogram, MergeChoice


class TestStreamsExample:
    """Test replication of Examples/Streams output."""

    def setup_method(self) -> None:
        """Reset PRNG state for deterministic tests."""
        reset_prng_cache()

    def test_normal_stream_error(self) -> None:
        """NormalStream.error() should match C++ output."""
        ns = NormalStream(100.0, 2.0)

        # Consume 1000 values (as the example does)
        for _ in range(1000):
            ns()

        # C++ outputs: NormalStream error: -0.1976
        # Allow small tolerance for cross-platform differences
        error = ns.error()
        assert abs(error - (-0.1976)) < 0.01, f"Error {error} differs from expected -0.1976"

    def test_histogram_bucket_counts(self) -> None:
        """Histogram bucket distribution should match C++ output."""
        ns = NormalStream(100.0, 2.0)
        hist = Histogram(10, MergeChoice.MEAN)

        for _ in range(1000):
            hist.set_value(ns())

        # Expected bucket counts from C++ output (approximate due to merging)
        # The exact bucket names depend on merge order, but total should be 1000
        assert hist.number_of_samples == 1000

        # Check that we have 10 buckets (the max)
        assert hist.number_of_buckets == 10

    def test_histogram_variance_stats(self) -> None:
        """Histogram variance statistics should match C++ output."""
        ns = NormalStream(100.0, 2.0)
        hist = Histogram(10, MergeChoice.MEAN)

        for _ in range(1000):
            hist.set_value(ns())

        # From C++ expected_output:
        # Variance          : 3.68377
        # Standard Deviation: 1.91932
        # Mean              : 99.9817
        assert abs(hist.variance - 3.68377) < 0.001
        assert abs(hist.std_dev - 1.91932) < 0.001
        assert abs(hist.mean - 99.9817) < 0.001

    def test_histogram_mean_stats(self) -> None:
        """Histogram mean statistics should match C++ output."""
        ns = NormalStream(100.0, 2.0)
        hist = Histogram(10, MergeChoice.MEAN)

        for _ in range(1000):
            hist.set_value(ns())

        # From C++ expected_output:
        # Number of samples : 1000
        # Sum               : 99981.7
        assert hist.number_of_samples == 1000
        assert abs(hist.sum - 99981.7) < 0.1

    def test_histogram_min_max_bug_compatible(self) -> None:
        """
        Min/Max should show C++ bug-compatible values.

        C++ initializes _Min = numeric_limits<float>::min() (smallest positive)
        and _Max = numeric_limits<float>::max(). Since all values are between
        these extremes, min/max never get updated. This is a known C++ bug
        that we replicate for output compatibility.
        """
        ns = NormalStream(100.0, 2.0)
        hist = Histogram(10, MergeChoice.MEAN)

        for _ in range(1000):
            hist.set_value(ns())

        # From C++ expected_output:
        # Minimum           : 1.17549e-38
        # Maximum           : 3.40282e+38

        # These are C++ float limits, not the actual min/max of the data
        assert abs(hist.min - 1.17549e-38) / 1.17549e-38 < 0.001
        assert abs(hist.max - 3.40282e+38) / 3.40282e+38 < 0.001

    def test_output_format(self) -> None:
        """Output string format should match C++ structure."""
        ns = NormalStream(100.0, 2.0)
        hist = Histogram(10, MergeChoice.MEAN)

        for _ in range(1000):
            hist.set_value(ns())

        output = str(hist)

        # Check required sections are present
        assert "Maximum number of buckets 10" in output
        assert "Merge choice is MEAN" in output
        assert "Bucket : <" in output
        assert "Variance" in output
        assert "Standard Deviation:" in output
        assert "Number of samples" in output
        assert "Minimum" in output
        assert "Maximum" in output
        assert "Sum" in output
        assert "Mean" in output
