"""
Validation test for Examples/Stats.

Compares Python output against C++SIM Examples/Stats/expected_output.

Expected output:
    NormalStream error: -0.2802
    Quantile precentage : 0.95
    Value below which percentage occurs 103.855
    Bucket : < 97.5433, 1 >
    ... (20 buckets total)
    Variance          : 3.84068
    Standard Deviation: 1.95977
    Number of samples : 20
    Minimum           : 1.17549e-38
    Maximum           : 3.40282e+38
    Sum               : 2014.45
    Mean              : 100.722
"""

import pytest

from pysim.random import NormalStream, reset_prng_cache
from pysim.stats import Quantile


class TestStatsExample:
    """Test replication of Examples/Stats output."""

    def setup_method(self) -> None:
        """Reset state for deterministic tests."""
        reset_prng_cache()

    def test_quantile_bucket_count(self) -> None:
        """Quantile should collect 20 samples into 20 buckets (all unique values)."""
        reset_prng_cache()
        stream = NormalStream(100.0, 2.0)
        hist = Quantile()

        for _ in range(20):
            hist.set_value(stream())

        # 20 unique values should create 20 buckets
        assert hist.number_of_buckets == 20
        assert hist.number_of_samples == 20

    def test_quantile_95th_percentile(self) -> None:
        """
        Quantile at 95% should match expected value.

        Expected: Value below which percentage occurs 103.855
        """
        reset_prng_cache()
        stream = NormalStream(100.0, 2.0)
        hist = Quantile(0.95)

        for _ in range(20):
            hist.set_value(stream())

        # 95th percentile of 20 samples = 19th value when sorted
        quantile_value = hist()
        assert abs(quantile_value - 103.855) < 0.01, (
            f"Expected ~103.855, got {quantile_value}"
        )

    def test_quantile_statistics(self) -> None:
        """
        Statistics should match expected output.

        Expected:
            Variance          : 3.84068
            Standard Deviation: 1.95977
            Sum               : 2014.45
            Mean              : 100.722
        """
        reset_prng_cache()
        stream = NormalStream(100.0, 2.0)
        hist = Quantile()

        for _ in range(20):
            hist.set_value(stream())

        # Check statistics
        assert abs(hist.variance - 3.84068) < 0.001, (
            f"Expected variance ~3.84068, got {hist.variance}"
        )
        assert abs(hist.std_dev - 1.95977) < 0.001, (
            f"Expected std dev ~1.95977, got {hist.std_dev}"
        )
        assert abs(hist.sum - 2014.45) < 0.1, (
            f"Expected sum ~2014.45, got {hist.sum}"
        )
        assert abs(hist.mean - 100.722) < 0.01, (
            f"Expected mean ~100.722, got {hist.mean}"
        )

    def test_normal_stream_error(self) -> None:
        """
        NormalStream error should match expected value.

        Expected: NormalStream error: -0.2802

        Note: The Error() method consumes 10000 samples, which advances
        the stream state significantly. We test after the histogram
        is populated.
        """
        reset_prng_cache()
        stream = NormalStream(100.0, 2.0)
        hist = Quantile()

        for _ in range(20):
            hist.set_value(stream())

        error = stream.error()
        # The error value depends on the exact stream state after 20 samples
        # then 10000 more for the error calculation
        assert abs(error - (-0.2802)) < 0.01, (
            f"Expected error ~-0.2802, got {error}"
        )

    def test_quantile_output_format(self) -> None:
        """Verify the output format matches expected pattern."""
        reset_prng_cache()
        stream = NormalStream(100.0, 2.0)
        hist = Quantile()

        for _ in range(20):
            hist.set_value(stream())

        output = str(hist)

        # Check structure
        assert "Quantile precentage : 0.95" in output
        assert "Value below which percentage occurs" in output
        assert "Bucket : <" in output
        assert "Variance" in output
        assert "Standard Deviation" in output
        assert "Number of samples : 20" in output
        assert "Mean" in output
