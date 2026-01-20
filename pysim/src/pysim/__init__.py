"""
PySim - Python port of C++SIM discrete event simulation library.

A SIMULA-style process-based discrete event simulation library.
"""

from pysim.process import Process, Scheduler
from pysim.entity import Entity, Semaphore, TriggerQueue
from pysim.random import (
    RandomStream,
    UniformStream,
    ExponentialStream,
    ErlangStream,
    HyperExponentialStream,
    NormalStream,
    TriangularStream,
    Draw,
    reset_prng_cache,
)
from pysim.stats import (
    Mean,
    Variance,
    Histogram,
    PrecisionHistogram,
    SimpleHistogram,
    Quantile,
    TimeVariance,
    Pareto,
)
from pysim.simset import Head, Link, Linkage

__version__ = "0.1.0"
__all__ = [
    # Core
    "Process",
    "Scheduler",
    # Entity/Events
    "Entity",
    "Semaphore",
    "TriggerQueue",
    # SimSet (SIMULA linked lists)
    "Head",
    "Link",
    "Linkage",
    # Random
    "RandomStream",
    "UniformStream",
    "ExponentialStream",
    "ErlangStream",
    "HyperExponentialStream",
    "NormalStream",
    "TriangularStream",
    "Draw",
    "reset_prng_cache",
    # Statistics
    "Mean",
    "Variance",
    "Histogram",
    "PrecisionHistogram",
    "SimpleHistogram",
    "Quantile",
    "TimeVariance",
    "Pareto",
]
