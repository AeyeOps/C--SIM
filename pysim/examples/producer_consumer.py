"""
Producer-Consumer example with bounded buffer.

Port of C++SIM Examples/Producer-Consumer.

Demonstrates:
- Entity-based processes with semaphore synchronization
- Bounded buffer (queue size 10) with blocking on full/empty
- ExponentialStream for inter-arrival times
- Simulation runs for 10000 time units

Expected output: 974 jobs produced and consumed (matches C++ expected_output).
"""

from __future__ import annotations

import simpy

from pysim import Entity, ExponentialStream, Scheduler, Semaphore, reset_prng_cache


class Job:
    """Simple job placeholder."""

    pass


class Queue:
    """Bounded buffer with max size."""

    def __init__(self, max_size: int = 10) -> None:
        self._jobs: list[Job] = []
        self._max_size = max_size

    def is_empty(self) -> bool:
        return len(self._jobs) == 0

    def is_full(self) -> bool:
        return len(self._jobs) >= self._max_size

    def enqueue(self, job: Job) -> None:
        self._jobs.append(job)

    def dequeue(self) -> Job | None:
        return self._jobs.pop(0) if self._jobs else None


class Producer(Entity):
    """Produces jobs and adds them to the queue."""

    def __init__(
        self,
        mean: float,
        job_queue: Queue,
        producer_sem: Semaphore,
        consumer_sem: Semaphore,
        stats: dict,
        env: simpy.Environment,
    ) -> None:
        super().__init__(env)
        self._inter_arrival = ExponentialStream(mean)
        self._queue = job_queue
        self._producer_sem = producer_sem
        self._consumer_sem = consumer_sem
        self._stats = stats

    def body(self):
        while True:
            job = Job()

            # Block if queue is full
            if self._queue.is_full():
                yield from self._producer_sem.get(self)

            self._stats["produced"] += 1
            self._queue.enqueue(job)
            yield from self._consumer_sem.release()

            yield from self.hold(self._inter_arrival())


class Consumer(Entity):
    """Consumes jobs from the queue."""

    def __init__(
        self,
        mean: float,
        job_queue: Queue,
        producer_sem: Semaphore,
        consumer_sem: Semaphore,
        stats: dict,
        env: simpy.Environment,
    ) -> None:
        super().__init__(env)
        self._inter_arrival = ExponentialStream(mean)
        self._queue = job_queue
        self._producer_sem = producer_sem
        self._consumer_sem = consumer_sem
        self._stats = stats

    def body(self):
        while True:
            # Block if queue is empty
            if self._queue.is_empty():
                yield from self._consumer_sem.get(self)

            job = self._queue.dequeue()
            yield from self._producer_sem.release()
            self._stats["consumed"] += 1

            yield from self.hold(self._inter_arrival())


def main() -> None:
    # Reset PRNG cache for reproducible output
    reset_prng_cache()
    Scheduler.terminate()

    # Create SimPy environment and scheduler
    env = simpy.Environment()
    Scheduler.scheduler(env)

    # Create shared state
    job_queue = Queue(max_size=10)
    producer_sem = Semaphore(resources=0, env=env)
    consumer_sem = Semaphore(resources=0, env=env)
    stats = {"produced": 0, "consumed": 0}

    # Create producer and consumer with mean inter-arrival of 10
    producer = Producer(10.0, job_queue, producer_sem, consumer_sem, stats, env)
    consumer = Consumer(10.0, job_queue, producer_sem, consumer_sem, stats, env)

    # Activate both
    producer.activate()
    consumer.activate()

    # Run simulation
    Scheduler.resume()
    env.run(until=10000)

    # Print results (matches C++ expected_output format)
    print(f"Total number of jobs present {stats['produced']}")
    print(f"Total number of jobs processed {stats['consumed']}")

    # Cleanup
    Scheduler.terminate()


if __name__ == "__main__":
    main()
