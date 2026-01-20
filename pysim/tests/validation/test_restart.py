"""
Validation test for Examples/Restart.

Compares Python behavior against C++SIM Examples/Restart/expected_output.

Expected output sequence:
    Iteration 0
    Tester holding.
        Harness holding.
        Harness holding and checking.
    Tester woken.
        Harness reset function called.
    [... repeats for iterations 1, 2, 3 ...]
    Iteration 3
    ...
        Harness passivated.
    End of simulation reached.

The test validates:
- Scheduler.reset() calls Process.reset() on scheduled processes
- Proper iteration through simulation cycles
- Process passivation at end of simulation
"""

import pytest
import simpy

from pysim.process import Process, Scheduler
from pysim.random import reset_prng_cache


class TestRestartExample:
    """Test replication of Examples/Restart behavior."""

    def setup_method(self) -> None:
        """Reset state for deterministic tests."""
        reset_prng_cache()
        Scheduler.terminate()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        Scheduler.terminate()

    def test_process_reset_callback(self) -> None:
        """
        Test that Process.reset() is called when Scheduler.reset() is invoked.

        The C++ implementation calls reset() on each process in the queue.
        """
        reset_prng_cache()
        env = simpy.Environment()
        Scheduler.scheduler(env)

        reset_called = {"count": 0}

        class TestProcess(Process):
            def __init__(self, env: simpy.Environment) -> None:
                super().__init__(env)

            def body(self):
                yield from self.hold(1000)

            def reset(self) -> None:
                reset_called["count"] += 1

        proc = TestProcess(env)
        proc.activate()

        # Run a bit
        env.run(until=10)

        # Reset scheduler - should call reset() on proc
        Scheduler.scheduler().reset()

        assert reset_called["count"] == 1, (
            f"Expected reset() called once, got {reset_called['count']}"
        )

    def test_iteration_sequence(self) -> None:
        """
        Test the iteration sequence from Examples/Restart.

        The Tester activates Harness, holds, then resets the scheduler.
        Each reset should call Harness.reset() which logs a message.
        """
        reset_prng_cache()
        env = simpy.Environment()
        Scheduler.scheduler(env)

        log = []
        iterations = 4

        class Harness(Process):
            """Process that gets reset each iteration."""

            def __init__(self, env: simpy.Environment) -> None:
                super().__init__(env)
                self._status = False
                self._do_passivate = False

            def body(self):
                self._status = True

                if self._do_passivate:
                    log.append("\tHarness passivated.")
                    yield from self.passivate()
                    return

                log.append("\tHarness holding.")
                yield from self.hold(10)

                log.append("\tHarness holding and checking.")
                yield from self.hold(1000)

                log.append("\tHarness passivated.")
                yield from self.passivate()

            def reset(self) -> None:
                log.append("\tHarness reset function called.")
                self._status = False

            def do_passivate(self) -> None:
                self._do_passivate = True

        # Run the simulation manually (mimicking C++ Tester)
        harness = Harness(env)

        for i in range(iterations):
            log.append(f"Iteration {i}")

            # Reset for new iteration
            harness._status = False
            harness._terminated = False
            harness._passivated = True
            harness._simpy_process = None

            harness.activate()

            log.append("Tester holding.")
            env.run(until=env.now + 100)

            log.append("Tester woken.")

            # Reset scheduler - calls reset() on processes
            Scheduler.scheduler().reset()

        # Final iteration - harness should passivate
        harness.do_passivate()
        harness._terminated = False
        harness._passivated = True
        harness._simpy_process = None
        harness.activate()
        env.run(until=env.now + 100)

        log.append("End of simulation reached.")

        # Verify key sequence elements
        assert log[0] == "Iteration 0", f"Expected 'Iteration 0', got {log[0]}"
        assert "Tester holding." in log
        assert "\tHarness holding." in log
        assert "Tester woken." in log
        assert "\tHarness reset function called." in log
        assert "Iteration 3" in log
        assert "\tHarness passivated." in log
        assert "End of simulation reached." in log

        # Count reset calls - should be exactly 4 (once per iteration)
        reset_calls = [l for l in log if "reset function called" in l]
        assert len(reset_calls) == 4, (
            f"Expected 4 reset calls, got {len(reset_calls)}"
        )

    def test_multiple_resets(self) -> None:
        """
        Test that multiple reset() calls work correctly.

        The C++ example calls Scheduler.reset() 4 times.
        """
        reset_prng_cache()
        env = simpy.Environment()
        Scheduler.scheduler(env)

        reset_count = {"value": 0}

        class CountingProcess(Process):
            def body(self):
                yield from self.hold(1000)

            def reset(self) -> None:
                reset_count["value"] += 1

        proc = CountingProcess(env)

        # Simulate 4 iterations
        for _ in range(4):
            proc._terminated = False
            proc._passivated = True
            proc._simpy_process = None
            proc.activate()
            env.run(until=env.now + 100)
            Scheduler.scheduler().reset()

        assert reset_count["value"] == 4, (
            f"Expected 4 reset calls, got {reset_count['value']}"
        )

    def test_scheduler_reset_clears_queue(self) -> None:
        """
        Test that Scheduler.reset() clears the queue.

        After reset(), no processes should be scheduled.
        """
        reset_prng_cache()
        env = simpy.Environment()
        sched = Scheduler.scheduler(env)

        class DummyProcess(Process):
            def body(self):
                yield from self.hold(1000)

        p1 = DummyProcess(env)
        p2 = DummyProcess(env)

        p1.activate()
        p2.activate_delay(10)

        # Both should be scheduled
        assert len(sched._process_map) >= 1

        # Reset should clear the queue
        sched.reset()

        # Queue should be empty
        assert len(sched._process_map) == 0, (
            f"Expected empty queue after reset, got {len(sched._process_map)}"
        )
