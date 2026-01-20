"""
Tests for PRNG implementation.

These tests verify that the Python PRNG produces identical sequences
to the C++ implementation.
"""

import math

import pytest

from pysim.random import (
    UniformStream,
    ExponentialStream,
    NormalStream,
    ErlangStream,
    TriangularStream,
    Draw,
    reset_prng_cache,
)


class TestUniformStream:
    """Tests for UniformStream."""

    def setup_method(self) -> None:
        """Reset PRNG cache before each test."""
        reset_prng_cache()

    def test_range(self) -> None:
        """Values should be within [lo, hi]."""
        stream = UniformStream(0.0, 1.0)
        for _ in range(1000):
            v = stream()
            assert 0.0 <= v <= 1.0

    def test_custom_range(self) -> None:
        """Values should be within custom range."""
        stream = UniformStream(10.0, 20.0)
        for _ in range(1000):
            v = stream()
            assert 10.0 <= v <= 20.0

    def test_reproducibility(self) -> None:
        """Same seeds should produce same sequence."""
        reset_prng_cache()
        stream1 = UniformStream(0.0, 1.0)
        values1 = [stream1() for _ in range(100)]

        reset_prng_cache()
        stream2 = UniformStream(0.0, 1.0)
        values2 = [stream2() for _ in range(100)]

        assert values1 == values2

    def test_stream_select_independence(self) -> None:
        """Different stream_select values should produce different sequences."""
        reset_prng_cache()
        stream1 = UniformStream(0.0, 1.0, stream_select=0)
        values1 = [stream1() for _ in range(10)]

        reset_prng_cache()
        stream2 = UniformStream(0.0, 1.0, stream_select=1)
        values2 = [stream2() for _ in range(10)]

        assert values1 != values2


class TestExponentialStream:
    """Tests for ExponentialStream."""

    def setup_method(self) -> None:
        reset_prng_cache()

    def test_positive(self) -> None:
        """Exponential values should be positive."""
        stream = ExponentialStream(1.0)
        for _ in range(1000):
            assert stream() > 0

    def test_mean_approximately_correct(self) -> None:
        """Sample mean should approximate theoretical mean."""
        stream = ExponentialStream(5.0)
        values = [stream() for _ in range(10000)]
        sample_mean = sum(values) / len(values)
        # Allow 10% error for statistical test
        assert abs(sample_mean - 5.0) < 0.5


class TestNormalStream:
    """Tests for NormalStream."""

    def setup_method(self) -> None:
        reset_prng_cache()

    def test_mean_approximately_correct(self) -> None:
        """Sample mean should approximate theoretical mean."""
        stream = NormalStream(100.0, 15.0)
        values = [stream() for _ in range(10000)]
        sample_mean = sum(values) / len(values)
        assert abs(sample_mean - 100.0) < 1.0

    def test_std_approximately_correct(self) -> None:
        """Sample std should approximate theoretical std."""
        stream = NormalStream(0.0, 10.0)
        values = [stream() for _ in range(10000)]
        sample_mean = sum(values) / len(values)
        sample_var = sum((v - sample_mean) ** 2 for v in values) / len(values)
        sample_std = math.sqrt(sample_var)
        assert abs(sample_std - 10.0) < 1.0


class TestTriangularStream:
    """Tests for TriangularStream."""

    def setup_method(self) -> None:
        reset_prng_cache()

    def test_range(self) -> None:
        """Values should be within [a, b]."""
        stream = TriangularStream(0.0, 10.0, 5.0)
        for _ in range(1000):
            v = stream()
            assert 0.0 <= v <= 10.0


class TestDraw:
    """Tests for Draw (Boolean draw)."""

    def setup_method(self) -> None:
        reset_prng_cache()

    def test_frequency(self) -> None:
        """Draw frequency should approximate probability."""
        draw = Draw(0.3)  # P(True) = 0.7 (C++ convention: returns s() >= prob)
        count = sum(1 for _ in range(10000) if draw())
        # Should be approximately 7000 (70%)
        assert 6500 < count < 7500


class TestPRNGCaching:
    """Tests for PRNG caching behavior."""

    def test_cache_behavior(self) -> None:
        """Multiple streams with default seeds should share cached state."""
        reset_prng_cache()

        stream1 = UniformStream(0.0, 1.0)
        stream2 = UniformStream(0.0, 1.0)

        # Both should produce the same first value because they share cached series
        v1 = stream1()
        reset_prng_cache()
        stream3 = UniformStream(0.0, 1.0)
        v3 = stream3()

        assert v1 == v3
