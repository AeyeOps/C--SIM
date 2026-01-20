"""
Validation test for Producer-Consumer example.

Compares Python output against C++SIM Examples/Producer-Consumer/expected_output.

Expected output:
    Total number of jobs present 974
    Total number of jobs processed 974
"""

import simpy
import pytest

from pysim.entity import Entity, Semaphore
from pysim.process import Scheduler
from pysim.random import ExponentialStream, reset_prng_cache


class Job:
    """Simple job marker."""
    pass


class Queue:
    """Fixed-capacity job queue."""

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
    """Produces jobs into the queue."""

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


class TestProducerConsumerExample:
    """Test replication of Examples/Producer-Consumer output."""

    def setup_method(self) -> None:
        """Reset state for deterministic tests."""
        reset_prng_cache()
        Scheduler.terminate()

    def test_producer_consumer_counts(self) -> None:
        """
        Producer and Consumer should process the same number of jobs.

        Expected output:
            Total number of jobs present 974
            Total number of jobs processed 974
        """
        env = simpy.Environment()
        Scheduler.scheduler(env)

        job_queue = Queue(max_size=10)
        producer_sem = Semaphore(resources=0, env=env)
        consumer_sem = Semaphore(resources=0, env=env)

        stats = {"produced": 0, "consumed": 0}

        producer = Producer(10.0, job_queue, producer_sem, consumer_sem, stats, env)
        consumer = Consumer(10.0, job_queue, producer_sem, consumer_sem, stats, env)

        producer.activate()
        consumer.activate()

        Scheduler.resume()
        env.run(until=10000)

        # C++ expected output: 974 jobs present and processed
        # With exact PRNG replication, we should get exactly 974
        assert stats["produced"] == stats["consumed"], (
            f"Mismatch: produced {stats['produced']}, consumed {stats['consumed']}"
        )

        # Exact validation against expected_output
        assert stats["produced"] == 974, (
            f"Expected 974 jobs produced (C++ expected_output), got {stats['produced']}"
        )
        assert stats["consumed"] == 974, (
            f"Expected 974 jobs consumed (C++ expected_output), got {stats['consumed']}"
        )

    def test_bounded_queue_semantics(self) -> None:
        """Verify bounded queue blocks producer when full."""
        env = simpy.Environment()
        Scheduler.terminate()
        Scheduler.scheduler(env)

        job_queue = Queue(max_size=3)
        producer_sem = Semaphore(resources=0, env=env)
        consumer_sem = Semaphore(resources=0, env=env)

        stats = {"produced": 0, "consumed": 0}

        # Create a fast producer (mean=1) and slow consumer (mean=5)
        producer = Producer(1.0, job_queue, producer_sem, consumer_sem, stats, env)
        consumer = Consumer(5.0, job_queue, producer_sem, consumer_sem, stats, env)

        producer.activate()
        consumer.activate()

        Scheduler.resume()
        env.run(until=100)

        # Both should have processed some jobs
        assert stats["produced"] > 0
        assert stats["consumed"] > 0
        # Producer should be blocked waiting for consumer at some point
        # resulting in roughly balanced counts (bounded queue)
        assert abs(stats["produced"] - stats["consumed"]) <= 5

    def test_semaphore_synchronization(self) -> None:
        """Verify semaphore properly synchronizes producer/consumer."""
        env = simpy.Environment()
        Scheduler.terminate()
        Scheduler.scheduler(env)

        # Minimal test: single produce/consume cycle
        producer_sem = Semaphore(resources=0, env=env)
        consumer_sem = Semaphore(resources=0, env=env)

        events = []

        class SingleProducer(Entity):
            def body(self_p):
                events.append(("produce", self_p.current_time()))
                yield from consumer_sem.release()
                events.append(("produce_done", self_p.current_time()))

        class SingleConsumer(Entity):
            def body(self_c):
                yield from consumer_sem.get(self_c)
                events.append(("consume", self_c.current_time()))

        p = SingleProducer(env)
        c = SingleConsumer(env)

        p.activate()
        c.activate()

        env.run(until=10)

        # Consumer should wait until producer releases
        assert events[0] == ("produce", 0.0)
        assert events[1] == ("produce_done", 0.0)
        assert events[2] == ("consume", 0.0)
