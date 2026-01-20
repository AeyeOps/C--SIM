"""
Statistics demonstration example.

Port of C++SIM Examples/Stats with additional demonstrations.

Demonstrates all statistics classes:
- Mean: Running mean calculation
- Variance: Mean + variance and standard deviation
- PrecisionHistogram: Auto-bucketing histogram
- SimpleHistogram: Fixed-width bucket histogram
- Quantile: Percentile calculation via histogram

Uses NormalStream to generate sample data.
"""

from __future__ import annotations

from pysim import (
    Mean,
    NormalStream,
    PrecisionHistogram,
    Quantile,
    SimpleHistogram,
    Variance,
    reset_prng_cache,
)


def demo_mean() -> None:
    """Demonstrate Mean class."""
    print("=" * 60)
    print("MEAN CLASS")
    print("=" * 60)
    print()

    mean = Mean()

    # Add some values
    values = [10, 20, 30, 40, 50]
    for v in values:
        mean += v

    print(f"Values: {values}")
    print(f"Number of samples: {mean.number_of_samples}")
    print(f"Sum: {mean.sum}")
    print(f"Mean: {mean.mean}")
    print()


def demo_variance() -> None:
    """Demonstrate Variance class."""
    print("=" * 60)
    print("VARIANCE CLASS")
    print("=" * 60)
    print()

    variance = Variance()

    # Generate samples from NormalStream
    stream = NormalStream(mean=50.0, std_dev=10.0)
    n_samples = 100

    print(f"Generating {n_samples} samples from NormalStream(mean=50, std_dev=10)")
    print()

    for _ in range(n_samples):
        variance += stream()

    print(f"Number of samples: {variance.number_of_samples}")
    print(f"Mean: {variance.mean:.4f}")
    print(f"Variance: {variance.variance:.4f}")
    print(f"Standard Deviation: {variance.std_dev:.4f}")
    print(f"95% Confidence Interval: +/- {variance.confidence(95.0):.4f}")
    print()


def demo_precision_histogram() -> None:
    """Demonstrate PrecisionHistogram class."""
    print("=" * 60)
    print("PRECISION HISTOGRAM CLASS")
    print("=" * 60)
    print()

    hist = PrecisionHistogram()

    # Generate samples
    stream = NormalStream(mean=100.0, std_dev=5.0)
    n_samples = 50

    print(f"Generating {n_samples} samples from NormalStream(mean=100, std_dev=5)")
    print()

    for _ in range(n_samples):
        hist.set_value(stream())

    print(f"Number of samples: {hist.number_of_samples}")
    print(f"Number of buckets: {hist.number_of_buckets}")
    print(f"Mean: {hist.mean:.4f}")
    print(f"Standard Deviation: {hist.std_dev:.4f}")
    print()
    print("First 5 buckets:")
    for i, bucket in enumerate(hist._buckets[:5]):
        print(f"  Bucket {i}: value={bucket.name:.4f}, count={bucket.count}")
    print()


def demo_simple_histogram() -> None:
    """Demonstrate SimpleHistogram class with fixed-width buckets."""
    print("=" * 60)
    print("SIMPLE HISTOGRAM CLASS")
    print("=" * 60)
    print()

    # Create histogram with range [0, 100] and 10 buckets (width=10 each)
    hist = SimpleHistogram(min_val=0, max_val=100, nbuckets=10)

    # Generate samples
    stream = NormalStream(mean=50.0, std_dev=15.0)
    n_samples = 100

    print(f"Histogram range: [0, 100] with 10 buckets (width={hist.width})")
    print(f"Generating {n_samples} samples from NormalStream(mean=50, std_dev=15)")
    print()

    for _ in range(n_samples):
        hist.set_value(stream())

    print(f"Number of samples: {hist.number_of_samples}")
    print()
    print("Bucket distribution:")
    for bucket in hist._buckets:
        bar = "*" * bucket.count
        print(f"  [{bucket.name:6.1f}]: {bucket.count:3d} {bar}")
    print()


def demo_quantile() -> None:
    """Demonstrate Quantile class (original C++ example)."""
    print("=" * 60)
    print("QUANTILE CLASS (Original C++ Example)")
    print("=" * 60)
    print()

    # This matches the original C++ Stats example
    stream = NormalStream(mean=100.0, std_dev=2.0)
    hist = Quantile()  # Default 95th percentile

    # Add 20 samples (matching C++ example)
    for _ in range(20):
        hist.set_value(stream())

    print(f"NormalStream error: {stream.error():.4f}")
    print()
    print(hist)


def demo_quantile_percentiles() -> None:
    """Demonstrate Quantile with different percentiles."""
    print("=" * 60)
    print("QUANTILE CLASS - Different Percentiles")
    print("=" * 60)
    print()

    # Generate shared data
    stream = NormalStream(mean=100.0, std_dev=10.0)
    data = [stream() for _ in range(200)]

    for q in [0.50, 0.75, 0.90, 0.95, 0.99]:
        quantile = Quantile(q=q)
        for v in data:
            quantile.set_value(v)
        print(f"  {int(q*100):2d}th percentile: {quantile.value:.4f}")
    print()


def main() -> None:
    # Reset PRNG cache for reproducible output
    reset_prng_cache()

    print()
    print("PySim Statistics Classes Demonstration")
    print("=" * 60)
    print()

    demo_mean()
    demo_variance()
    demo_precision_histogram()
    demo_simple_histogram()
    demo_quantile()
    demo_quantile_percentiles()

    print("=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
