"""
Machine Shop simulation example.

Port of C++SIM Examples/Basic.

Demonstrates:
- Process-based simulation with multiple interacting processes
- ExponentialStream for arrivals and service times
- UniformStream for machine failures/repairs (optional)
- Mean statistic for queue length tracking
- Running simulation until N jobs processed

Expected output (no breaks):
    Total number of jobs present ~1080
    Total number of jobs processed ~1079
    Average response time ~8.3

Run with --breaks flag to enable machine failures.
"""

from __future__ import annotations

import sys

import simpy

from pysim import ExponentialStream, Mean, Process, Scheduler, UniformStream, reset_prng_cache


class Job:
    """Job with arrival time tracking."""

    def __init__(self, arrival_time: float) -> None:
        self.arrival_time = arrival_time
        self.response_time = 0.0


class Machine(Process):
    """Machine that processes jobs from queue."""

    def __init__(
        self,
        env: simpy.Environment,
        mean_service: float,
        job_queue: list,
        mean_jobs: Mean,
        stats: dict,
    ) -> None:
        super().__init__(env)
        self._service_time = ExponentialStream(mean_service)
        self._job_queue = job_queue
        self._mean_jobs = mean_jobs
        self._stats = stats
        self._operational = True
        self._working = False
        self._wake_event: simpy.Event | None = None

    def body(self):
        while True:
            self._working = True

            while self._job_queue and self._operational:
                active_start = self.current_time()
                self._mean_jobs.set_value(len(self._job_queue))

                job = self._job_queue.pop(0)
                service = self._service_time()
                yield from self.hold(service)

                if not self._operational:
                    # Machine broke during service - put job back
                    self._job_queue.insert(0, job)
                    break

                active_end = self.current_time()
                self._stats["machine_active_time"] += active_end - active_start

                # Job completed
                job.response_time = active_end - job.arrival_time
                self._stats["total_response_time"] += job.response_time
                self._stats["processed_jobs"] += 1

            self._working = False
            # Wait to be woken up when new jobs arrive
            self._wake_event = self._env.event()
            yield self._wake_event
            self._wake_event = None

    def wake(self) -> None:
        """Wake machine when new jobs arrive or after repair."""
        if self._wake_event is not None and not self._wake_event.triggered:
            self._wake_event.succeed()

    @property
    def processing(self) -> bool:
        return self._working

    @property
    def operational(self) -> bool:
        return self._operational

    def broken(self) -> None:
        self._operational = False

    def fixed(self) -> None:
        self._operational = True


class Arrivals(Process):
    """Job arrivals with exponential inter-arrival time."""

    def __init__(
        self,
        env: simpy.Environment,
        mean_arrival: float,
        job_queue: list,
        machine: Machine,
        stats: dict,
    ) -> None:
        super().__init__(env)
        self._inter_arrival = ExponentialStream(mean_arrival)
        self._job_queue = job_queue
        self._machine = machine
        self._stats = stats

    def body(self):
        while True:
            yield from self.hold(self._inter_arrival())

            # Create job
            job = Job(self.current_time())
            was_empty = len(self._job_queue) == 0
            self._job_queue.append(job)
            self._stats["total_jobs"] += 1

            # Wake machine if it was idle
            if was_empty and not self._machine.processing and self._machine.operational:
                self._machine.wake()


class Breaks(Process):
    """Machine failure/repair process."""

    def __init__(
        self,
        env: simpy.Environment,
        machine: Machine,
        job_queue: list,
        stats: dict,
    ) -> None:
        super().__init__(env)
        self._repair_time = UniformStream(10, 100)
        self._operative_time = UniformStream(200, 500)
        self._machine = machine
        self._job_queue = job_queue
        self._stats = stats

    def body(self):
        while True:
            failed_time = self._repair_time()
            yield from self.hold(self._operative_time())

            self._machine.broken()

            yield from self.hold(failed_time)

            self._stats["machine_failed_time"] += failed_time
            self._machine.fixed()

            # Wake the machine after repair
            self._machine.wake()


def run_simulation(use_breaks: bool = False) -> None:
    """Run the machine shop simulation."""
    # Reset PRNG cache for reproducible output
    reset_prng_cache()
    Scheduler.terminate()

    # Create SimPy environment and scheduler
    env = simpy.Environment()
    Scheduler.scheduler(env)

    # Shared state
    job_queue: list[Job] = []
    mean_jobs = Mean()
    stats = {
        "total_jobs": 0,
        "processed_jobs": 0,
        "total_response_time": 0.0,
        "machine_active_time": 0.0,
        "machine_failed_time": 0.0,
    }

    # Create processes
    machine = Machine(env, mean_service=8.0, job_queue=job_queue, mean_jobs=mean_jobs, stats=stats)
    arrivals = Arrivals(env, mean_arrival=8.0, job_queue=job_queue, machine=machine, stats=stats)

    # Activate processes
    arrivals.activate()
    machine.activate()

    if use_breaks:
        breaks = Breaks(env, machine=machine, job_queue=job_queue, stats=stats)
        breaks.activate()

    # Run until 1000 jobs processed
    while stats["processed_jobs"] < 1000:
        env.step()

    final_time = env.now

    # Print results (matches C++ expected_output format)
    print(f"Total number of jobs present {stats['total_jobs']}")
    print(f"Total number of jobs processed {stats['processed_jobs']}")
    print(f"Total response time of {stats['total_response_time']:.2f}")
    print(f"Average response time = {stats['total_response_time'] / stats['processed_jobs']:.4f}")

    prob_working = (stats["machine_active_time"] - stats["machine_failed_time"]) / final_time
    print(f"Probability that machine is working = {prob_working:.6f}")

    if stats["machine_active_time"] > 0:
        prob_failed = stats["machine_failed_time"] / stats["machine_active_time"]
    else:
        prob_failed = 0
    print(f"Probability that machine has failed = {prob_failed:.6f}")

    print(f"Average number of jobs present = {mean_jobs.mean:.4f}")

    # Cleanup
    Scheduler.terminate()


def main() -> None:
    use_breaks = "--breaks" in sys.argv

    if use_breaks:
        print("Running Machine Shop with breaks (machine failures)")
    else:
        print("Running Machine Shop without breaks")
    print()

    run_simulation(use_breaks=use_breaks)


if __name__ == "__main__":
    main()
