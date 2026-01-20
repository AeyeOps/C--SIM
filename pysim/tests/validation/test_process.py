"""
Validation tests for concurrent Process execution.

Tests Process scheduling, activation, and time management.
"""

import simpy
import pytest

from pysim.process import Process, Scheduler, NEVER


class TestProcessConcurrency:
    """Test concurrent process execution."""

    def setup_method(self) -> None:
        """Reset scheduler for each test."""
        Scheduler.terminate()

    def test_multiple_processes_interleaved(self) -> None:
        """Multiple processes should interleave execution correctly."""
        env = simpy.Environment()
        Scheduler.scheduler(env)

        events = []

        class Worker(Process):
            def __init__(self_w, name: str, interval: float, env):
                super().__init__(env)
                self_w.name = name
                self_w.interval = interval

            def body(self_w):
                for i in range(3):
                    events.append((self_w.name, i, self_w.current_time()))
                    yield from self_w.hold(self_w.interval)

        w1 = Worker("A", 1.0, env)
        w2 = Worker("B", 1.5, env)

        w1.activate()
        w2.activate()

        env.run(until=10)

        # Extract times for each worker
        a_times = [t for (n, _, t) in events if n == "A"]
        b_times = [t for (n, _, t) in events if n == "B"]

        # A runs at 0, 1, 2
        assert a_times == [0.0, 1.0, 2.0]
        # B runs at 0, 1.5, 3.0
        assert b_times == [0.0, 1.5, 3.0]

    def test_process_current_after_hold(self) -> None:
        """Process.Current should be set correctly after hold()."""
        env = simpy.Environment()
        Scheduler.scheduler(env)

        current_after_hold = []

        class CurrentTracker(Process):
            def __init__(self_t, name: str, env):
                super().__init__(env)
                self_t.name = name

            def body(self_t):
                yield from self_t.hold(1.0)
                # After hold, Current should be set to self
                current_after_hold.append((self_t.name, Process.Current is self_t))
                yield from self_t.hold(1.0)
                current_after_hold.append((self_t.name, Process.Current is self_t))

        p1 = CurrentTracker("P1", env)
        p2 = CurrentTracker("P2", env)

        p1.activate()
        p2.activate()

        env.run(until=5)

        # Each process should see itself as Current after hold()
        for name, is_current in current_after_hold:
            assert is_current, f"Process {name} should be Current after hold()"

    def test_hold_advances_time(self) -> None:
        """hold() should advance simulation time correctly."""
        env = simpy.Environment()
        Scheduler.scheduler(env)

        times = []

        class TimeTracker(Process):
            def body(self_t):
                times.append(self_t.current_time())
                yield from self_t.hold(5.0)
                times.append(self_t.current_time())
                yield from self_t.hold(3.0)
                times.append(self_t.current_time())

        p = TimeTracker(env)
        p.activate()

        env.run(until=20)

        assert times == [0.0, 5.0, 8.0]

    def test_hold_negative_time_rejected(self) -> None:
        """hold() with negative time should be rejected."""
        env = simpy.Environment()
        Scheduler.scheduler(env)

        events = []

        class NegativeHolder(Process):
            def body(self_n):
                events.append(("before", self_n.current_time()))
                yield from self_n.hold(-5.0)  # Should do nothing
                events.append(("after", self_n.current_time()))

        p = NegativeHolder(env)
        p.activate()

        env.run(until=10)

        # Both events should be at time 0 (negative hold does nothing)
        assert events[0] == ("before", 0.0)
        assert events[1] == ("after", 0.0)


class TestProcessStates:
    """Test process state management."""

    def setup_method(self) -> None:
        """Reset scheduler for each test."""
        Scheduler.terminate()

    def test_process_idle_state(self) -> None:
        """Process.idle should reflect scheduling state."""
        env = simpy.Environment()
        Scheduler.scheduler(env)

        class IdleChecker(Process):
            def __init__(self_i, env):
                super().__init__(env)
                self_i.idle_before_hold = None
                self_i.idle_after_hold = None

            def body(self_i):
                self_i.idle_before_hold = self_i.idle
                yield from self_i.hold(1.0)
                self_i.idle_after_hold = self_i.idle

        p = IdleChecker(env)

        # Before activation, process should be idle
        assert p.idle is True

        p.activate()
        env.run(until=5)

        # After termination, should be idle again
        assert p.idle is True

    def test_process_terminated_state(self) -> None:
        """Process.terminated should be True after body() completes."""
        env = simpy.Environment()
        Scheduler.scheduler(env)

        class TerminatingProcess(Process):
            def body(self_t):
                yield from self_t.hold(1.0)

        p = TerminatingProcess(env)

        assert p.terminated is False

        p.activate()
        env.run(until=5)

        assert p.terminated is True

    def test_process_passivated_state(self) -> None:
        """Process.passivated should reflect passivation state."""
        env = simpy.Environment()
        Scheduler.scheduler(env)

        class PassivatingProcess(Process):
            def __init__(self_p, env):
                super().__init__(env)
                self_p.was_passivated = None

            def body(self_p):
                self_p.was_passivated = self_p.passivated
                yield from self_p.hold(1.0)

        p = PassivatingProcess(env)

        # Initially passivated
        assert p.passivated is True

        p.activate()

        # After activation, not passivated
        assert p.passivated is False

        env.run(until=5)

        # After termination, passivated again
        assert p.passivated is True


class TestProcessTermination:
    """Test process termination."""

    def setup_method(self) -> None:
        """Reset scheduler for each test."""
        Scheduler.terminate()

    def test_process_terminates_cleanly(self) -> None:
        """Process should terminate when body() completes."""
        env = simpy.Environment()
        Scheduler.scheduler(env)

        events = []

        class FiniteProcess(Process):
            def body(self_f):
                for i in range(3):
                    events.append(("tick", i, self_f.current_time()))
                    yield from self_f.hold(1.0)
                events.append(("done", self_f.current_time()))

        p = FiniteProcess(env)
        p.activate()

        env.run(until=20)

        assert len(events) == 4
        assert events[-1] == ("done", 3.0)
        assert p.terminated is True

    def test_cancel_updates_state(self) -> None:
        """cancel() should update process state."""
        env = simpy.Environment()
        Scheduler.scheduler(env)

        class CancellableProcess(Process):
            def body(self_c):
                yield from self_c.hold(100.0)

        p = CancellableProcess(env)
        p.activate()

        # Process is not idle while scheduled
        assert p.idle is False

        p.cancel()

        # After cancel, process becomes idle
        assert p.idle is True
        assert p.passivated is True


class TestSchedulerQueue:
    """Test Scheduler queue operations."""

    def setup_method(self) -> None:
        """Reset scheduler for each test."""
        Scheduler.terminate()

    def test_scheduler_reset(self) -> None:
        """Scheduler.reset() should clear all processes."""
        env = simpy.Environment()
        sched = Scheduler.scheduler(env)

        class DummyProcess(Process):
            def body(self_d):
                yield from self_d.hold(100.0)

        p1 = DummyProcess(env)
        p2 = DummyProcess(env)

        p1.activate()
        p2.activate()

        sched.reset()

        # Queue should be empty after reset
        assert sched.remove() is None

    def test_scheduler_singleton(self) -> None:
        """Scheduler should be a singleton."""
        env = simpy.Environment()
        s1 = Scheduler.scheduler(env)
        s2 = Scheduler.scheduler()  # No env needed for subsequent calls

        assert s1 is s2

    def test_scheduler_current_time(self) -> None:
        """Scheduler should track current simulation time."""
        env = simpy.Environment()
        sched = Scheduler.scheduler(env)

        assert sched.current_time() == 0.0

        class TimeAdvancer(Process):
            def body(self_a):
                yield from self_a.hold(5.0)

        p = TimeAdvancer(env)
        p.activate()

        env.run(until=10)

        assert sched.current_time() == 10.0
