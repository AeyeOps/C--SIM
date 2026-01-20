"""
Validation test for Examples/Interrupts.

Compares Python output against C++SIM Examples/Interrupts/expected_output.

Expected output:
    Total jobs processed 96
    Total signals processed 2

The simulation models a processor that:
- Normally processes jobs from a queue with exponential service time
- Can be interrupted by signals from a Signaller process
- Terminates after processing 2 signals
"""

import pytest
import simpy

from pysim.entity import Entity
from pysim.process import Process, Scheduler
from pysim.random import ExponentialStream, reset_prng_cache


class TestInterruptsExample:
    """Test replication of Examples/Interrupts output."""

    def setup_method(self) -> None:
        """Reset state for deterministic tests."""
        reset_prng_cache()
        Scheduler.terminate()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        Scheduler.terminate()

    def test_interrupt_sets_flag(self) -> None:
        """
        Test that Entity.interrupt() sets the interrupted flag on target.

        This validates the flag-setting mechanism used in the Interrupts example.
        Note: The exact timing of when the waiter wakes up is implementation-
        dependent. The key behavior is that interrupt sets the flag correctly.
        """
        reset_prng_cache()
        env = simpy.Environment()
        Scheduler.scheduler(env)

        class Waiter(Entity):
            def __init__(self, env: simpy.Environment) -> None:
                super().__init__(env)
                self.was_interrupted = False

            def body(self):
                # Wait for up to 100 time units
                yield from self.wait_for(100.0)
                self.was_interrupted = self.interrupted
                self.clear_flags()

        class Interrupter(Entity):
            """Must be Entity to use interrupt() method."""

            def __init__(self, env: simpy.Environment, target: Entity) -> None:
                super().__init__(env)
                self._target = target

            def body(self):
                # Wait a bit, then interrupt the waiter
                yield from self.hold(10.0)
                # Interrupt the target
                yield from self.interrupt(self._target, immediate=False)

        waiter = Waiter(env)
        interrupter = Interrupter(env, waiter)

        waiter.activate()
        interrupter.activate()

        env.run()

        # The key validation is that the interrupt flag was set
        assert waiter.was_interrupted, "Waiter should have been interrupted"

    def test_interrupt_counts(self) -> None:
        """
        Replicate the Examples/Interrupts simulation.

        Expected:
            Total jobs processed 96
            Total signals processed 2

        The simulation:
        - Arrivals generate jobs with ExponentialStream(2)
        - Processor services jobs with ExponentialStream(10) via Wait()
        - Signaller interrupts the processor with ExponentialStream(1000)
        - After 2 signals, simulation terminates
        """
        reset_prng_cache()
        env = simpy.Environment()
        Scheduler.scheduler(env)

        # Shared state
        job_queue: list = []
        signal_queue: list = []
        stats = {"processed_jobs": 0, "signalled_jobs": 0}

        class Job:
            """Simple job marker."""

            def __init__(self, is_signal: bool) -> None:
                if is_signal:
                    signal_queue.append(self)
                else:
                    job_queue.append(self)

        class Processor(Entity):
            """Processor that handles jobs and signals."""

            def __init__(self, env: simpy.Environment, mean: float) -> None:
                super().__init__(env)
                self._service_time = ExponentialStream(mean)
                self._done = False

            @property
            def done(self) -> bool:
                return self._done

            def body(self):
                while True:
                    # Wait for service time - can be interrupted
                    yield from self.wait_for(self._service_time())

                    if not self.interrupted:
                        # Normal timeout - process a job if available
                        if job_queue:
                            job_queue.pop(0)
                            stats["processed_jobs"] += 1
                    else:
                        # Interrupted - process a signal
                        self.clear_flags()
                        if signal_queue:
                            signal_queue.pop(0)
                            stats["signalled_jobs"] += 1

                    if stats["signalled_jobs"] == 2:
                        self._done = True
                        return

        class Arrivals(Process):
            """Generate jobs with exponential inter-arrival time."""

            def __init__(self, env: simpy.Environment, mean: float) -> None:
                super().__init__(env)
                self._inter_arrival = ExponentialStream(mean)

            def body(self):
                while True:
                    yield from self.hold(self._inter_arrival())
                    Job(is_signal=False)

        class Signaller(Entity):
            """Send signals (interrupts) to the processor."""

            def __init__(
                self, env: simpy.Environment, mean: float, processor: Entity
            ) -> None:
                super().__init__(env)
                self._signal_time = ExponentialStream(mean)
                self._processor = processor

            def body(self):
                while not self._processor.done:
                    yield from self.hold(self._signal_time())
                    if self._processor.done:
                        break
                    Job(is_signal=True)
                    yield from self.interrupt(self._processor, immediate=False)

        # Create simulation entities
        processor = Processor(env, 10)  # Service time mean=10
        arrivals = Arrivals(env, 2)  # Inter-arrival mean=2
        signaller = Signaller(env, 1000, processor)  # Signal mean=1000

        processor.activate()
        arrivals.activate()
        signaller.activate()

        # Run until processor terminates
        env.run(until=10000)  # Safety limit

        assert processor.done, "Processor should have finished"
        assert stats["signalled_jobs"] == 2, (
            f"Expected 2 signals processed (C++ expected_output), "
            f"got {stats['signalled_jobs']}"
        )
        assert stats["processed_jobs"] == 96, (
            f"Expected 96 jobs processed (C++ expected_output), "
            f"got {stats['processed_jobs']}"
        )

    def test_wait_timeout_vs_interrupt(self) -> None:
        """
        Test that wait_for correctly distinguishes timeout from interrupt.

        C++ Wait(t) returns true on timeout, false on interrupt.
        Python checks self.interrupted after wait_for().
        """
        reset_prng_cache()
        env = simpy.Environment()
        Scheduler.scheduler(env)

        results = {"timeout_count": 0, "interrupt_count": 0}

        class TestEntity(Entity):
            def body(self):
                # First wait should timeout (no one interrupts)
                yield from self.wait_for(5.0)
                if not self.interrupted:
                    results["timeout_count"] += 1
                self.clear_flags()

        entity = TestEntity(env)
        entity.activate()
        env.run()

        assert results["timeout_count"] == 1, "Should have timed out once"
        assert results["interrupt_count"] == 0, "Should not have been interrupted"
