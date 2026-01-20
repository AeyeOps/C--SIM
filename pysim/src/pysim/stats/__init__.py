"""Statistics collection classes."""

from pysim.stats.mean import Mean
from pysim.stats.variance import Variance
from pysim.stats.histogram import Bucket, PrecisionHistogram, Histogram, MergeChoice
from pysim.stats.simple_histogram import SimpleHistogram
from pysim.stats.quantile import Quantile
from pysim.stats.time_variance import TimeVariance
from pysim.stats.pareto import Pareto

__all__ = [
    "Mean",
    "Variance",
    "Bucket",
    "PrecisionHistogram",
    "Histogram",
    "SimpleHistogram",
    "MergeChoice",
    "Quantile",
    "TimeVariance",
    "Pareto",
]
