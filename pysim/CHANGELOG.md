# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-19

### Added
- Initial Python port of C++SIM discrete event simulation library
- Core classes: Process, Scheduler
- Entity/Event classes: Entity, Semaphore, TriggerQueue
- Random streams: UniformStream, ExponentialStream, NormalStream, ErlangStream, HyperExponentialStream, TriangularStream, Draw
- Statistics: Mean, Variance, Histogram, PrecisionHistogram, SimpleHistogram, Quantile, TimeVariance, Pareto
- SimSet linked lists: Head, Link, Linkage (SIMULA SIMSET equivalents)
- 77 validation tests against C++ expected_output files
- Example scripts: producer_consumer.py, machine_shop.py, stats_demo.py

### Changed
- Uses SimPy as underlying simulation engine instead of pthreads
- Generator-based coroutines instead of OS threads
- Python 3.12+ required

### Notes
- PRNG produces identical sequences to C++SIM with same seeds
- API mirrors C++SIM where possible, adapted for Python idioms
- All `hold()`, `wait()`, and semaphore operations require `yield from`
