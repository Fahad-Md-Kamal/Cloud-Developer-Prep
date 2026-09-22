"""
Fault Tolerance Patterns for Enterprise Distributed Systems
-----------------------------------------------------------

This module demonstrates circuit breakers, bulkheads, retries with
exponential backoff, and graceful degradation helpers that Lawstronaut and
Optimizely rely on to keep APIs responsive during upstream failures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import random
import threading
import time
from typing import Any, Callable, TypeVar


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    """Raised when a circuit breaker blocks a call."""


@dataclass
class CircuitBreaker:
    """Minimal circuit breaker suitable for orchestrating remote calls."""

    failure_threshold: int = 3
    recovery_timeout: float = 5.0
    name: str = "breaker"
    _failure_count: int = field(default=0, init=False)
    _state: str = field(default="CLOSED", init=False)
    _opened_at: float | None = field(default=None, init=False)

    def _can_attempt(self) -> bool:
        if self._state == "OPEN" and self._opened_at is not None:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.recovery_timeout:
                self._state = "HALF_OPEN"
                logging.info("[%s] moving to HALF_OPEN", self.name)
            else:
                return False
        return True

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        if not self._can_attempt():
            raise CircuitOpenError(f"{self.name} circuit is open; rejecting call")

        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            self._failure_count += 1
            logging.warning("[%s] failure (%s/%s)", self.name, self._failure_count, self.failure_threshold)
            if self._failure_count >= self.failure_threshold:
                self._state = "OPEN"
                self._opened_at = time.monotonic()
                logging.error("[%s] opening circuit", self.name)
            raise
        else:
            self._failure_count = 0
            self._state = "CLOSED"
            self._opened_at = None
            return result


class Bulkhead:
    """Protect shared resources by limiting concurrent access."""

    def __init__(self, max_concurrent: int) -> None:
        self._sem = threading.Semaphore(max_concurrent)

    def run(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        acquired = self._sem.acquire(timeout=1)
        if not acquired:
            raise RuntimeError("bulkhead saturated")
        try:
            return func(*args, **kwargs)
        finally:
            self._sem.release()


def retry_with_backoff(func: Callable[..., T], attempts: int = 3, base_delay: float = 0.1) -> T:
    """Retry helper with exponential backoff and jitter."""
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except Exception as exc:
            last_exc = exc
            sleep_for = base_delay * (2 ** (attempt - 1)) + random.uniform(0, base_delay)
            logging.warning("attempt %s failed (%s); sleeping %.2fs", attempt, exc, sleep_for)
            time.sleep(sleep_for)
    raise RuntimeError("max retries exceeded") from last_exc


def graceful_degradation(primary: Callable[[], T], fallback: Callable[[Exception], T]) -> T:
    """Run the primary handler and fall back when it raises."""
    try:
        return primary()
    except Exception as exc:
        logging.error("primary handler failed; degrading gracefully: %s", exc)
        return fallback(exc)


def _flaky_legal_feed() -> str:
    """Simulate a Lawstronaut crawler call with intermittent failures."""
    if random.random() < 0.4:
        raise ConnectionError("transient upstream timeout")
    return "latest legal corpus chunk"


def simulate_fault_tolerant_pipeline() -> None:
    """Demonstrate how the pieces compose for a resilient workflow."""
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=2, name="crawler")
    bulkhead = Bulkhead(max_concurrent=2)

    def protected_call() -> str:
        return bulkhead.run(lambda: breaker.call(_flaky_legal_feed))

    def fallback(_: Exception) -> str:
        return "serve cached corpus snapshot"

    for _ in range(5):
        result = graceful_degradation(lambda: retry_with_backoff(protected_call), fallback)
        logging.info("delivered payload: %s", result)
        time.sleep(0.5)


if __name__ == "__main__":
    simulate_fault_tolerant_pipeline()
