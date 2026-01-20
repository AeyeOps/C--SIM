"""
Entity, Semaphore, and TriggerQueue - non-causal event handling.

Port of C++SIM Event/ module.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, Generator

import simpy

from pysim.process import Process

if TYPE_CHECKING:
    from simpy import Environment


class TriggerQueue:
    """
    Queue of entities waiting for triggers.

    From Event/TriggerQueue.cc.
    """

    def __init__(self) -> None:
        self._queue: list[Entity] = []

    def __len__(self) -> int:
        return len(self._queue)

    def empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._queue) == 0

    def insert(self, entity: Entity) -> None:
        """
        Add entity to wait queue.

        Entity must not already be waiting.
        """
        if entity.is_waiting:
            return  # Cannot wait for multiple events
        self._queue.append(entity)

    def remove(self) -> Entity | None:
        """Remove and return first entity, or None if empty."""
        return self._queue.pop(0) if self._queue else None

    def trigger_first(self, set_trigger: bool = True) -> bool:
        """
        Wake first waiting entity.

        Returns False if queue empty.
        """
        if not self._queue:
            return False

        entity = self.remove()
        if entity is None:
            return False

        if set_trigger:
            entity.set_triggered()

        # Must succeed the wait event to unblock the yield in wait()
        if entity._wait_event is not None and not entity._wait_event.triggered:
            entity._wait_event.succeed()

        entity.activate_at(Process.current_time(), prior=True)
        return True

    def trigger_all(self) -> bool:
        """
        Wake all waiting entities.

        Returns False if queue was empty.
        """
        if not self._queue:
            return False

        count = len(self._queue)
        for _ in range(count):
            self.trigger_first()
        return True


class Entity(Process):
    """
    Process with interrupt/wait capabilities.

    Extends Process with non-causal event handling:
    - Wait/WaitFor: suspend until triggered or interrupted
    - Interrupt/trigger: wake waiting entities

    From Event/Entity.cc.
    """

    def __init__(self, env: Environment | None = None) -> None:
        super().__init__(env)
        self._waiting: bool = False
        self._interrupted: bool = False
        self._triggered: bool = False
        self._wait_event: simpy.Event | None = None

    @property
    def is_waiting(self) -> bool:
        """Check if entity is in wait state."""
        return self._waiting

    @property
    def interrupted(self) -> bool:
        """Check if entity was interrupted."""
        return self._interrupted

    @property
    def triggered(self) -> bool:
        """Check if entity was triggered."""
        return self._triggered

    def set_triggered(self) -> None:
        """Set the triggered flag."""
        self._triggered = True

    def clear_flags(self) -> None:
        """Clear interrupted and triggered flags."""
        self._interrupted = False
        self._triggered = False

    def wait(self) -> Generator[simpy.Event, None, None]:
        """
        Wait indefinitely for trigger or interrupt.

        From Entity.cc Wait() implementation.
        """
        self._waiting = True
        self._wait_event = self._env.event()

        try:
            yield self._wait_event
        except simpy.Interrupt:
            self._interrupted = True
        finally:
            self._waiting = False
            self._wait_event = None

    def wait_for(self, timeout: float) -> Generator[simpy.Event, None, None]:
        """
        Wait with timeout for trigger or interrupt.

        From Entity.cc WaitFor() implementation.
        """
        self._waiting = True
        self._wait_event = self._env.event()

        try:
            # Wait for either the event or timeout
            result = yield self._wait_event | self._env.timeout(timeout)
            # If timeout occurred and event wasn't triggered, it's a timeout
            if self._wait_event not in result:
                pass  # Timeout - no flag set
        except simpy.Interrupt:
            self._interrupted = True
        finally:
            self._waiting = False
            self._wait_event = None

    def wait_for_trigger(self, queue: TriggerQueue) -> Generator[simpy.Event, None, None]:
        """
        Wait on a trigger queue.

        Entity is added to queue and waits until triggered.
        """
        queue.insert(self)
        yield from self.wait()

    def wait_for_semaphore(self, sem: "Semaphore") -> Generator[simpy.Event, None, None]:
        """Wait on a semaphore."""
        yield from sem.get(self)

    def interrupt(self, target: Entity, immediate: bool = True) -> Generator[simpy.Event, None, bool]:
        """
        Interrupt another entity.

        From Entity.cc:157-193.

        Args:
            target: Entity to interrupt
            immediate: If True, yield control after interrupting

        Returns:
            True if interrupt was delivered, False if target not interruptible
        """
        if target.terminated or not target._waiting:
            yield from ()  # Empty generator for type consistency
            return False

        target._interrupted = True

        # Wake the target by triggering its wait event
        if target._wait_event is not None and not target._wait_event.triggered:
            target._wait_event.succeed()

        target.activate_at(Process.current_time(), prior=True)

        if immediate:
            yield self._env.timeout(0)

        return True

    def trigger(self, target: Entity) -> Generator[simpy.Event, None, None]:
        """
        Trigger another entity (like interrupt but sets triggered flag).

        Args:
            target: Entity to trigger
        """
        if target.terminated or not target._waiting:
            return

        target._triggered = True

        # Wake the target
        if target._wait_event is not None and not target._wait_event.triggered:
            target._wait_event.succeed()

        target.activate_at(Process.current_time(), prior=True)
        yield self._env.timeout(0)


class Semaphore:
    """
    Counting semaphore with optional ceiling.

    From Event/Semaphore.cc.
    """

    class Outcome(Enum):
        DONE = auto()
        NOTDONE = auto()
        WOULD_BLOCK = auto()

    def __init__(
        self,
        resources: int = 1,
        ceiling: bool = False,
        env: Environment | None = None,
    ) -> None:
        if env is None:
            from pysim.process import Scheduler
            env = Scheduler.scheduler().env
        self._env = env
        self._waiting_list = TriggerQueue()
        self._num_waiting = 0
        self._total_resources = resources
        self._current_resources = resources
        self._has_ceiling = ceiling

    @property
    def number_waiting(self) -> int:
        """Number of entities waiting for the semaphore."""
        return self._num_waiting

    @property
    def available(self) -> int:
        """Number of available resources."""
        return self._current_resources

    def get(self, entity: Entity) -> Generator[simpy.Event, None, Outcome]:
        """
        Acquire resource. Suspends entity if none available.

        From Semaphore.cc:82-106.
        """
        if self._current_resources > 0:
            self._current_resources -= 1
        else:
            self._num_waiting += 1
            self._waiting_list.insert(entity)
            entity.cancel()
            # Entity must yield after this returns
            yield from entity.wait()

        return Semaphore.Outcome.DONE

    def try_get(self, entity: Entity) -> Outcome:
        """
        Non-blocking acquire.

        Returns WOULD_BLOCK if no resources available.
        From Semaphore.cc:108-114.
        """
        if self._current_resources == 0:
            return Semaphore.Outcome.WOULD_BLOCK

        self._current_resources -= 1
        return Semaphore.Outcome.DONE

    def release(self) -> Generator[simpy.Event, None, Outcome]:
        """
        Release resource.

        IMPORTANT: Yields control if a waiter is awakened.
        From Semaphore.cc:121-148.

        This is a generator that must be consumed with `yield from`.
        Both branches yield to ensure consistent generator behavior.
        """
        if self._num_waiting > 0:
            self._num_waiting -= 1
            self._waiting_list.trigger_first(set_trigger=False)
            # C++SIM yields control here - critical for correct scheduling
            yield self._env.timeout(0)
        else:
            self._current_resources += 1
            if self._has_ceiling and self._current_resources > self._total_resources:
                self._current_resources = self._total_resources
            # Yield empty to maintain generator semantics (no-op if no waiters)
            yield from ()
        return Semaphore.Outcome.DONE
