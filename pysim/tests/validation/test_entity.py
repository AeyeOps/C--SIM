"""
Validation tests for Entity wait/interrupt functionality.

Tests the non-causal event handling from Event/Entity module.
"""

import simpy
import pytest

from pysim.entity import Entity, TriggerQueue, Semaphore
from pysim.process import Process, Scheduler


class TestEntityWaitInterrupt:
    """Test Entity wait and interrupt mechanisms."""

    def setup_method(self) -> None:
        """Reset scheduler for each test."""
        Scheduler.terminate()

    def test_wait_and_trigger(self) -> None:
        """Entity.wait() should block until triggered."""
        env = simpy.Environment()
        Scheduler.scheduler(env)

        events = []

        class Waiter(Entity):
            def body(self_w):
                events.append(("wait_start", self_w.current_time()))
                yield from self_w.wait()
                events.append(("wait_end", self_w.current_time(), self_w.triggered))

        class Triggerer(Entity):
            def __init__(self_t, target: Entity, env):
                super().__init__(env)
                self_t.target = target

            def body(self_t):
                yield from self_t.hold(5.0)
                events.append(("trigger", self_t.current_time()))
                yield from self_t.trigger(self_t.target)

        waiter = Waiter(env)
        triggerer = Triggerer(waiter, env)

        waiter.activate()
        triggerer.activate()

        env.run(until=20)

        assert events[0] == ("wait_start", 0.0)
        assert events[1] == ("trigger", 5.0)
        assert events[2][0] == "wait_end"
        assert events[2][1] == 5.0
        assert events[2][2] is True  # triggered flag set

    def test_wait_and_interrupt(self) -> None:
        """Entity.wait() should be interruptible."""
        env = simpy.Environment()
        Scheduler.scheduler(env)

        events = []

        class Waiter(Entity):
            def body(self_w):
                events.append(("wait_start", self_w.current_time()))
                yield from self_w.wait()
                events.append(("wait_end", self_w.current_time(), self_w.interrupted))

        class Interrupter(Entity):
            def __init__(self_i, target: Entity, env):
                super().__init__(env)
                self_i.target = target

            def body(self_i):
                yield from self_i.hold(3.0)
                events.append(("interrupt", self_i.current_time()))
                yield from self_i.interrupt(self_i.target)

        waiter = Waiter(env)
        interrupter = Interrupter(waiter, env)

        waiter.activate()
        interrupter.activate()

        env.run(until=20)

        assert events[0] == ("wait_start", 0.0)
        assert events[1] == ("interrupt", 3.0)
        assert events[2][0] == "wait_end"
        assert events[2][1] == 3.0
        assert events[2][2] is True  # interrupted flag set

    def test_wait_for_timeout(self) -> None:
        """Entity.wait_for() should timeout if not triggered."""
        env = simpy.Environment()
        Scheduler.scheduler(env)

        events = []

        class TimedWaiter(Entity):
            def body(self_w):
                events.append(("wait_start", self_w.current_time()))
                yield from self_w.wait_for(5.0)
                events.append((
                    "wait_end",
                    self_w.current_time(),
                    self_w.triggered,
                    self_w.interrupted,
                ))

        waiter = TimedWaiter(env)
        waiter.activate()

        env.run(until=20)

        assert events[0] == ("wait_start", 0.0)
        assert events[1][0] == "wait_end"
        assert events[1][1] == 5.0  # Timeout at 5.0
        assert events[1][2] is False  # Not triggered
        assert events[1][3] is False  # Not interrupted

    def test_wait_for_triggered_before_timeout(self) -> None:
        """Entity.wait_for() should return early if triggered."""
        env = simpy.Environment()
        Scheduler.scheduler(env)

        events = []

        class TimedWaiter(Entity):
            def body(self_w):
                events.append(("wait_start", self_w.current_time()))
                yield from self_w.wait_for(10.0)
                events.append(("wait_end", self_w.current_time(), self_w.triggered))

        class Triggerer(Entity):
            def __init__(self_t, target: Entity, env):
                super().__init__(env)
                self_t.target = target

            def body(self_t):
                yield from self_t.hold(3.0)
                events.append(("trigger", self_t.current_time()))
                yield from self_t.trigger(self_t.target)

        waiter = TimedWaiter(env)
        triggerer = Triggerer(waiter, env)

        waiter.activate()
        triggerer.activate()

        env.run(until=20)

        assert events[0] == ("wait_start", 0.0)
        assert events[1] == ("trigger", 3.0)
        assert events[2][0] == "wait_end"
        assert events[2][1] == 3.0  # Triggered before timeout
        assert events[2][2] is True  # triggered flag set


class TestTriggerQueue:
    """Test TriggerQueue functionality."""

    def setup_method(self) -> None:
        """Reset scheduler for each test."""
        Scheduler.terminate()

    def test_trigger_queue_fifo(self) -> None:
        """TriggerQueue should wake entities in FIFO order."""
        env = simpy.Environment()
        Scheduler.scheduler(env)

        events = []
        queue = TriggerQueue()

        class QueueWaiter(Entity):
            def __init__(self_w, name: str, env):
                super().__init__(env)
                self_w.name = name

            def body(self_w):
                events.append((f"{self_w.name}_wait", self_w.current_time()))
                yield from self_w.wait_for_trigger(queue)
                events.append((f"{self_w.name}_done", self_w.current_time()))

        class QueueTriggerer(Entity):
            def body(self_t):
                yield from self_t.hold(5.0)
                events.append(("trigger_first", self_t.current_time()))
                queue.trigger_first()
                yield from self_t.hold(0)  # Allow triggered process to run

                yield from self_t.hold(5.0)
                events.append(("trigger_second", self_t.current_time()))
                queue.trigger_first()

        w1 = QueueWaiter("w1", env)
        w2 = QueueWaiter("w2", env)
        triggerer = QueueTriggerer(env)

        w1.activate()
        w2.activate()
        triggerer.activate()

        env.run(until=20)

        # w1 and w2 wait at time 0
        assert events[0] == ("w1_wait", 0.0)
        assert events[1] == ("w2_wait", 0.0)
        # First trigger at time 5 wakes w1 (FIFO)
        assert events[2] == ("trigger_first", 5.0)
        assert events[3] == ("w1_done", 5.0)
        # Second trigger at time 10 wakes w2
        assert events[4] == ("trigger_second", 10.0)
        assert events[5] == ("w2_done", 10.0)

    def test_trigger_all(self) -> None:
        """TriggerQueue.trigger_all() should wake all waiting entities."""
        env = simpy.Environment()
        Scheduler.scheduler(env)

        events = []
        queue = TriggerQueue()

        class MultiWaiter(Entity):
            def __init__(self_w, name: str, env):
                super().__init__(env)
                self_w.name = name

            def body(self_w):
                yield from self_w.wait_for_trigger(queue)
                events.append((self_w.name, self_w.current_time()))

        class AllTriggerer(Entity):
            def body(self_t):
                yield from self_t.hold(3.0)
                queue.trigger_all()

        w1 = MultiWaiter("w1", env)
        w2 = MultiWaiter("w2", env)
        w3 = MultiWaiter("w3", env)
        triggerer = AllTriggerer(env)

        w1.activate()
        w2.activate()
        w3.activate()
        triggerer.activate()

        env.run(until=10)

        # All should be triggered at time 3
        assert len(events) == 3
        for name, time in events:
            assert time == 3.0


class TestEntityFlags:
    """Test Entity flag management."""

    def setup_method(self) -> None:
        """Reset scheduler for each test."""
        Scheduler.terminate()

    def test_clear_flags(self) -> None:
        """Entity.clear_flags() should reset triggered and interrupted."""
        env = simpy.Environment()
        Scheduler.scheduler(env)

        class FlagTest(Entity):
            def body(self_e):
                self_e._triggered = True
                self_e._interrupted = True
                assert self_e.triggered is True
                assert self_e.interrupted is True

                self_e.clear_flags()
                assert self_e.triggered is False
                assert self_e.interrupted is False

                yield from self_e.hold(0)  # Must yield at least once

        e = FlagTest(env)
        e.activate()
        env.run(until=1)

    def test_is_waiting_flag(self) -> None:
        """Entity.is_waiting should reflect wait state."""
        env = simpy.Environment()
        Scheduler.scheduler(env)

        waiting_states = []

        class WaitingTest(Entity):
            def body(self_e):
                waiting_states.append(("before", self_e.is_waiting))
                # Start wait but get triggered immediately
                yield from self_e.wait_for(0.001)
                waiting_states.append(("after", self_e.is_waiting))

        e = WaitingTest(env)
        e.activate()
        env.run(until=1)

        assert waiting_states[0] == ("before", False)
        assert waiting_states[1] == ("after", False)


class TestInterruptNonWaiting:
    """Test interrupt behavior for non-waiting entities."""

    def setup_method(self) -> None:
        """Reset scheduler for each test."""
        Scheduler.terminate()

    def test_interrupt_non_waiting_returns_false(self) -> None:
        """Interrupt on non-waiting entity should return False."""
        env = simpy.Environment()
        Scheduler.scheduler(env)

        result = []

        class NonWaiter(Entity):
            def body(self_n):
                yield from self_n.hold(100)

        class Interrupter(Entity):
            def __init__(self_i, target: Entity, env):
                super().__init__(env)
                self_i.target = target

            def body(self_i):
                yield from self_i.hold(1.0)
                # Target is holding, not waiting
                gen = self_i.interrupt(self_i.target)
                # Consume the generator
                try:
                    while True:
                        yield next(gen)
                except StopIteration as e:
                    result.append(e.value)

        target = NonWaiter(env)
        interrupter = Interrupter(target, env)

        target.activate()
        interrupter.activate()

        env.run(until=10)

        assert result == [False]
