# PySim

Python port of C++SIM discrete event simulation library.

A SIMULA-style process-based discrete event simulation library using SimPy as the underlying engine.

## Relationship to C++SIM

PySim is a Python port of [C++SIM](https://github.com/nmcl/C--SIM), a discrete event process-based simulation library that has been under development since 1990. C++SIM implements SIMULA-style co-routines using OS threads (primarily pthreads).

PySim preserves the C++SIM API where possible while adapting to Python idioms:
- Generator-based coroutines instead of OS threads
- SimPy as the underlying simulation engine
- Type hints throughout for IDE support

## Installation

```bash
pip install pysim
```

Or with uv:

```bash
uv add pysim
```

For development:

```bash
git clone <repository>
cd pysim
uv sync --dev
```

## Quick Start

```python
import simpy
from pysim import Process, Scheduler

class MyProcess(Process):
    def body(self):
        print(f"Started at {self.current_time()}")
        yield from self.hold(10.0)
        print(f"Finished at {self.current_time()}")

# Setup
env = simpy.Environment()
Scheduler.scheduler(env)

# Create and run
proc = MyProcess(env)
proc.activate()
env.run()
```

## Examples

See the `examples/` directory for complete, runnable examples:

| Example | Description |
|---------|-------------|
| `producer_consumer.py` | Classic bounded buffer with semaphores |
| `machine_shop.py` | Job arrivals, machine processing, optional failures |
| `stats_demo.py` | Histogram and quantile statistics |

Run examples:

```bash
python examples/producer_consumer.py
python examples/machine_shop.py
python examples/machine_shop.py --breaks  # with machine failures
python examples/stats_demo.py
```

## API Reference

### Core Classes

#### Process

Base class for simulation processes. All simulation objects needing independent execution must derive from Process and implement `body()`.

```python
class MyProcess(Process):
    def body(self):
        # Main process logic - must be a generator
        yield from self.hold(5.0)  # Suspend for 5 time units
```

Key methods:
- `body()` - Abstract method, the process's main execution (must yield)
- `hold(t)` - Suspend for simulated time t (`yield from self.hold(t)`)
- `activate()` - Schedule process to run now
- `activate_at(time)` - Schedule process at specific time
- `activate_delay(delay)` - Schedule process after delay
- `passivate()` - Make process idle indefinitely
- `terminate_process()` - End process execution
- `current_time()` - Get current simulation time

#### Scheduler

Central simulation controller (singleton).

```python
env = simpy.Environment()
sched = Scheduler.scheduler(env)  # Get or create singleton

# After simulation
Scheduler.terminate()  # Reset singleton
```

### Entity and Events

#### Entity

Extends Process with interrupt/wait capabilities for non-causal event handling.

```python
class MyEntity(Entity):
    def body(self):
        yield from self.wait()  # Wait indefinitely for trigger
        if self.interrupted:
            print("Was interrupted!")
        elif self.triggered:
            print("Was triggered!")
```

Key methods:
- `wait()` - Wait indefinitely for trigger or interrupt
- `wait_for(timeout)` - Wait with timeout
- `interrupt(target)` - Interrupt another entity
- `trigger(target)` - Trigger another entity

#### Semaphore

Counting semaphore for process synchronization.

```python
sem = Semaphore(resources=1, env=env)

# In a process body:
yield from sem.get(self)   # Acquire (blocks if none available)
yield from sem.release()   # Release
```

#### TriggerQueue

Queue of entities waiting for triggers.

```python
queue = TriggerQueue()
queue.insert(entity)       # Add entity to wait queue
queue.trigger_first()      # Wake first waiting entity
queue.trigger_all()        # Wake all waiting entities
```

### Random Streams

All random streams produce identical sequences to C++SIM with the same seeds.

| Class | Description |
|-------|-------------|
| `UniformStream(lo, hi)` | Uniform distribution on [lo, hi] |
| `ExponentialStream(mean)` | Exponential distribution |
| `NormalStream(mean, std_dev)` | Normal (Gaussian) distribution |
| `ErlangStream(mean, std_dev)` | Erlang distribution |
| `HyperExponentialStream(mean, std_dev)` | Hyperexponential (CV > 1) |
| `TriangularStream(a, b, c)` | Triangular distribution |
| `Draw(p)` | Boolean with probability p |

```python
from pysim import ExponentialStream, reset_prng_cache

# Reset for reproducible results
reset_prng_cache()

stream = ExponentialStream(mean=10.0)
value = stream()  # Generate next value
```

### Statistics

| Class | Description |
|-------|-------------|
| `Mean` | Running mean calculation |
| `Variance` | Mean, variance, and standard deviation |
| `Histogram` | General histogram with configurable buckets |
| `PrecisionHistogram` | Auto-bucketing histogram |
| `SimpleHistogram` | Fixed-width bucket histogram |
| `Quantile` | Percentile calculation via histogram |

```python
from pysim import Mean, Quantile

mean = Mean()
mean += 1.0
mean += 2.0
mean += 3.0
print(mean.mean)  # 2.0

quantile = Quantile(q=0.95)  # 95th percentile
for value in data:
    quantile.set_value(value)
print(quantile.value)  # 95th percentile value
```

### SimSet (Linked Lists)

SIMULA SIMSET-style linked list classes for queue management.

| Class | Description |
|-------|-------------|
| `Head` | List head (anchor) |
| `Link` | List element that can be linked |
| `Linkage` | Base class for linkable objects |

## Migration from C++SIM

Key differences when porting C++SIM code:

| C++SIM | PySim |
|--------|-------|
| `Hold(t)` | `yield from self.hold(t)` |
| `Body()` method | `body()` generator method |
| `Activate()` | `activate()` |
| Thread-based | Generator-based coroutines |
| `Semaphore.Get()` | `yield from sem.get(self)` |
| `Semaphore.Release()` | `yield from sem.release()` |

Important: All methods that suspend execution (`hold`, `wait`, `passivate`, semaphore operations) must use `yield from`.

## Testing

Run the test suite:

```bash
uv run pytest tests/ -v
```

The test suite includes 77 validation tests that compare Python output against C++SIM expected_output files.

## Features

- Process-based simulation with SIMULA-style API
- Entity/Semaphore/TriggerQueue for non-causal event handling
- SimSet linked lists (Head, Link, Linkage)
- Statistical distributions (Uniform, Exponential, Normal, etc.)
- Statistics collection (Mean, Variance, Histogram, Quantile)
- Full type hints for IDE support
- Deterministic PRNG matching C++SIM sequences
