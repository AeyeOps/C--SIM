"""
Process and Scheduler - core simulation classes.

Port of C++SIM ClassLib/Process.cc with SimPy as the underlying engine.

Scheduling Architecture
-----------------------
This implementation uses a hybrid approach:

1. **SimPy Environment**: Drives the actual simulation event loop via
   generator-based coroutines. Process.hold() yields SimPy timeouts.

2. **Custom Scheduler Queue**: Maintains a priority queue for ActivateBefore/After
   semantics that SimPy doesn't natively support. This queue tracks scheduling
   order but SimPy's event loop controls actual execution timing.

The custom Scheduler is primarily for:
- ActivateBefore/ActivateAfter relative scheduling
- Process.Current tracking
- C++SIM-compatible API (idle(), evtime, etc.)

For simple simulations using only hold()/activate_delay(), SimPy's internal
scheduler handles timing correctly. The custom queue adds overhead only for
relative scheduling operations.
"""

from __future__ import annotations

import heapq
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generator

import simpy

if TYPE_CHECKING:
    from simpy import Environment

# Sentinel for "never wake up"
NEVER = -1.0


@dataclass(order=True)
class ScheduledProcess:
    """Entry in the ready queue for priority scheduling."""

    time: float
    priority: int = field(compare=True)  # Lower = higher priority
    counter: int = field(compare=True)  # Tie-breaker for insertion order
    process: "Process" = field(compare=False)


class Scheduler:
    """
    Central simulation controller.

    Manages simulation time and the ready queue of processes.
    Provides singleton access via scheduler() class method.

    Port of C++SIM Scheduler class (Process.cc:89-137).
    """

    _instance: Scheduler | None = None
    _running: bool = False

    def __init__(self, env: Environment) -> None:
        self._env = env
        self._queue: list[ScheduledProcess] = []
        self._counter = 0
        self._process_map: dict[Process, ScheduledProcess] = {}

    @classmethod
    def scheduler(cls, env: Environment | None = None) -> Scheduler:
        """Get or create the singleton scheduler."""
        if cls._instance is None:
            if env is None:
                raise ValueError("Environment required for first scheduler access")
            cls._instance = Scheduler(env)
        return cls._instance

    @classmethod
    def terminate(cls) -> None:
        """Terminate the scheduler and reset singleton."""
        if cls._instance is not None:
            cls._running = False
            cls._instance = None

    @classmethod
    def simulation_started(cls) -> bool:
        """Check if simulation is running."""
        return cls._running

    @classmethod
    def suspend(cls) -> None:
        """Suspend simulation."""
        cls._running = False

    @classmethod
    def resume(cls) -> None:
        """Resume simulation."""
        cls._running = True

    @property
    def env(self) -> Environment:
        """Get the SimPy environment."""
        return self._env

    def current_time(self) -> float:
        """Current simulation time."""
        return self._env.now

    def reset(self) -> None:
        """
        Reset simulation: cancel all processes and clear the queue.

        NOTE: SimPy environments cannot reset time to 0. For a fresh
        simulation run, create a new simpy.Environment and Scheduler:

            Scheduler.terminate()
            env = simpy.Environment()
            Scheduler.scheduler(env)

        From Process.cc:109-126.
        """
        while self._queue:
            entry = heapq.heappop(self._queue)
            proc = entry.process
            if proc in self._process_map:
                del self._process_map[proc]
            proc.cancel()
            proc.reset()

    def insert(self, process: Process, prior: bool = False) -> None:
        """
        Insert process into ready queue.

        Args:
            process: Process to schedule
            prior: If True, insert with higher priority at same time
        """
        if process in self._process_map:
            return  # Already scheduled

        priority = 0 if prior else 1
        entry = ScheduledProcess(process.evtime, priority, self._counter, process)
        self._counter += 1
        heapq.heappush(self._queue, entry)
        self._process_map[process] = entry

    def remove(self, process: Process | None = None) -> Process | None:
        """
        Remove process from queue.

        If process is None, removes and returns the next scheduled process.
        """
        if process is None:
            # Remove next scheduled
            while self._queue:
                entry = heapq.heappop(self._queue)
                if entry.process in self._process_map:
                    del self._process_map[entry.process]
                    return entry.process
            return None
        else:
            # Remove specific process
            if process in self._process_map:
                del self._process_map[process]
                # Note: We don't actually remove from heap - it becomes stale
                return process
            return None

    def insert_before(self, process: Process, before: Process) -> bool:
        """
        Insert process to run just before another process.

        From Process.cc:211-221.
        """
        if before not in self._process_map:
            return False

        before_entry = self._process_map[before]
        # Same time, but priority one less (higher)
        entry = ScheduledProcess(
            before_entry.time,
            before_entry.priority - 1,
            self._counter,
            process,
        )
        self._counter += 1
        heapq.heappush(self._queue, entry)
        self._process_map[process] = entry
        process._wakeuptime = before_entry.time
        return True

    def insert_after(self, process: Process, after: Process) -> bool:
        """
        Insert process to run just after another process.

        From Process.cc:223-233.
        """
        if after not in self._process_map:
            return False

        after_entry = self._process_map[after]
        # Same time, but priority one more (lower)
        entry = ScheduledProcess(
            after_entry.time,
            after_entry.priority + 1,
            self._counter,
            process,
        )
        self._counter += 1
        heapq.heappush(self._queue, entry)
        self._process_map[process] = entry
        process._wakeuptime = after_entry.time
        return True

    def get_next(self, process: Process) -> Process | None:
        """Get the process scheduled after the given process."""
        # This is approximate - we'd need a more sophisticated data structure
        # for exact SIMULA semantics
        if process not in self._process_map:
            return None
        current_entry = self._process_map[process]
        for entry in sorted(self._queue):
            if entry.time > current_entry.time or (
                entry.time == current_entry.time and entry.counter > current_entry.counter
            ):
                return entry.process
        return None

    def print_queue(self) -> str:
        """Return string representation of scheduler queue."""
        lines = ["Scheduler queue:"]
        for entry in sorted(self._queue):
            if entry.process in self._process_map:
                lines.append(f"  t={entry.time:.4f} p={entry.priority} {entry.process}")
        lines.append("End of scheduler queue.")
        return "\n".join(lines)


class Process(ABC):
    """
    Base class for simulation processes.

    All simulation objects needing independent execution must derive from
    Process and implement the body() method.

    Port of C++SIM Process class (Process.cc:141-510).

    Note: The `Current` class variable tracks the currently executing process.
    In C++SIM, this is updated by the thread scheduler on every context switch.
    In PySim, it is updated when `hold()` resumes execution. This may be stale
    after other yield points (e.g., waiting on SimPy events). Use `current_time()`
    instead of relying on `Process.Current` when possible.
    """

    # Class-level current process tracking (see docstring for limitations)
    Current: Process | None = None
    Never: float = NEVER

    def __init__(self, env: Environment | None = None) -> None:
        if env is None:
            env = Scheduler.scheduler().env
        self._env = env
        self._wakeuptime: float = NEVER
        self._terminated: bool = False
        self._passivated: bool = True
        self._simpy_process: simpy.Process | None = None
        self._passivate_event: simpy.Event | None = None

    @property
    def env(self) -> Environment:
        """Get the SimPy environment."""
        return self._env

    @property
    def evtime(self) -> float:
        """Scheduled wakeup time."""
        return self._wakeuptime

    @property
    def terminated(self) -> bool:
        """Check if process has terminated."""
        return self._terminated

    @property
    def passivated(self) -> bool:
        """Check if process is passivated (idle and not scheduled)."""
        return self._passivated

    @property
    def idle(self) -> bool:
        """
        Check if process is idle (not running and not scheduled).

        From Process.n:110-113.
        """
        return self._wakeuptime < self.current_time()

    @staticmethod
    def current_time() -> float:
        """Get current simulation time."""
        sched = Scheduler._instance
        return sched.current_time() if sched else 0.0

    @classmethod
    def current(cls) -> Process | None:
        """Get currently executing process."""
        return cls.Current

    def set_evtime(self, time: float) -> None:
        """
        Set wakeup time for scheduled process.

        From Process.cc:181-195.
        """
        if not self.idle:
            if time >= self.current_time():
                self._wakeuptime = time
            else:
                print(f"Process.set_evtime - time {time} invalid")
        else:
            print("Process.set_evtime called for idle process.")

    def next_ev(self) -> Process | None:
        """Return process scheduled after this one."""
        if self.idle:
            return None
        return Scheduler.scheduler().get_next(self)

    @abstractmethod
    def body(self) -> Generator[simpy.Event, None, None]:
        """
        Main process execution.

        Must be implemented by subclasses. This is the SIMULA Body() equivalent.
        """
        ...

    def _run_wrapper(self) -> Generator[simpy.Event, None, None]:
        """Wrapper that sets Current and handles termination."""
        Process.Current = self
        try:
            yield from self.body()
        finally:
            self._terminated = True
            self._passivated = True
            self._wakeuptime = NEVER

    # Activation methods (Process.cc:211-272)

    def activate(self) -> None:
        """
        Activate at current time with priority.

        From Process.cc:264-272.
        """
        if self._terminated or not self.idle:
            return

        self._passivated = False
        self._wakeuptime = self.current_time()
        Scheduler.scheduler().insert(self, prior=True)

        if self._simpy_process is None:
            self._simpy_process = self._env.process(self._run_wrapper())

    def activate_at(self, time: float, prior: bool = False) -> None:
        """
        Activate at specified time.

        From Process.cc:243-252.
        """
        if time < self.current_time() or self._terminated or not self.idle:
            return

        self._passivated = False
        self._wakeuptime = time
        Scheduler.scheduler().insert(self, prior)

        if self._simpy_process is None:
            self._simpy_process = self._env.process(self._run_wrapper())

    def activate_delay(self, delay: float, prior: bool = False) -> None:
        """
        Activate after delay.

        From Process.cc:254-262.
        """
        if delay < 0 or self._terminated or not self.idle:
            return

        self._passivated = False
        self._wakeuptime = self.current_time() + delay
        Scheduler.scheduler().insert(self, prior)

        if self._simpy_process is None:
            self._simpy_process = self._env.process(self._run_wrapper())

    def activate_before(self, p: Process) -> None:
        """
        Activate just before another process.

        From Process.cc:211-221.
        """
        if self._terminated or not self.idle:
            return

        self._passivated = False
        if not Scheduler.scheduler().insert_before(self, p):
            print("ActivateBefore failed because 'before' process is not scheduled")
            return

        if self._simpy_process is None:
            self._simpy_process = self._env.process(self._run_wrapper())

    def activate_after(self, p: Process) -> None:
        """
        Activate just after another process.

        From Process.cc:223-233.
        """
        if self._terminated or not self.idle:
            return

        self._passivated = False
        if not Scheduler.scheduler().insert_after(self, p):
            print("ActivateAfter failed because 'after' process is not scheduled")
            return

        if self._simpy_process is None:
            self._simpy_process = self._env.process(self._run_wrapper())

    # Reactivation methods (Process.cc:280-328)

    def reactivate(self) -> Generator[simpy.Event, None, None]:
        """Reactivate at current time."""
        if self._terminated:
            yield from ()  # Empty generator for type consistency
            return
        self._unschedule()
        self.activate()
        if Process.Current is self:
            yield self._env.timeout(0)

    def reactivate_at(self, time: float, prior: bool = False) -> Generator[simpy.Event, None, None]:
        """Reactivate at specified time."""
        if self._terminated:
            yield from ()
            return
        self._unschedule()
        self.activate_at(time, prior)
        if Process.Current is self:
            yield self._env.timeout(0)

    def reactivate_delay(
        self, delay: float, prior: bool = False
    ) -> Generator[simpy.Event, None, None]:
        """Reactivate after delay."""
        if self._terminated:
            yield from ()
            return
        self._unschedule()
        self.activate_delay(delay, prior)
        if Process.Current is self:
            yield self._env.timeout(0)

    def reactivate_before(self, p: Process) -> Generator[simpy.Event, None, None]:
        """Reactivate just before another process."""
        if self._terminated:
            yield from ()
            return
        self._unschedule()
        self.activate_before(p)
        if Process.Current is self:
            yield self._env.timeout(0)

    def reactivate_after(self, p: Process) -> Generator[simpy.Event, None, None]:
        """Reactivate just after another process."""
        if self._terminated:
            yield from ()
            return
        self._unschedule()
        self.activate_after(p)
        if Process.Current is self:
            yield self._env.timeout(0)

    def _unschedule(self) -> None:
        """
        Remove from scheduler queue.

        From Process.cc:369-378.
        """
        if not self.idle:
            if self is not Process.Current:
                Scheduler.scheduler().remove(self)
            self._wakeuptime = NEVER
            self._passivated = True

    # Process control (Process.cc:380-472)

    def hold(self, t: float) -> Generator[simpy.Event, None, None]:
        """
        Suspend for simulated time t.

        This method both updates the custom scheduler queue (via activate_delay)
        and yields a SimPy timeout. SimPy's event loop controls actual timing;
        the custom scheduler tracks state for C++SIM API compatibility.

        Usage: yield from process.hold(5.0)

        From Process.cc:427-445.
        """
        if t < 0:
            print(f"Process.hold - time {t} invalid.")
            return

        self._wakeuptime = NEVER
        self.activate_delay(t)
        yield self._env.timeout(t)

        # Update Current AFTER the yield returns - this is when the process resumes
        # This is necessary because SimPy doesn't update our Process.Current when switching coroutines
        Process.Current = self

    def passivate(self) -> Generator[simpy.Event, None, None]:
        """
        Suspend indefinitely (make idle).

        From Process.n:117-121.
        """
        if not self._passivated:
            self.cancel()
            # Create an event that will never trigger
            self._passivate_event = self._env.event()
            yield self._passivate_event

            # Update Current AFTER the yield returns - this is when the process resumes
            Process.Current = self

    def cancel(self) -> None:
        """
        Cancel next burst of activity.

        From Process.cc:386-401.
        """
        if not self.idle:
            self._unschedule()
            # Note: In SimPy we can't truly suspend mid-execution
            # The caller must yield after calling cancel

    def terminate_process(self) -> None:
        """
        Terminate this process.

        From Process.cc:449-472.
        """
        if self._terminated:
            return

        if self is not Process.Current:
            self._unschedule()

        self._terminated = True
        self._passivated = True
        self._wakeuptime = NEVER

        if self._simpy_process is not None:
            try:
                self._simpy_process.interrupt()
            except RuntimeError:
                pass  # Already terminated

    def reset(self) -> None:
        """
        User-overridable reset hook.

        Called by Scheduler.reset() for each process.
        From Process.cc:403-408.
        """
        pass
