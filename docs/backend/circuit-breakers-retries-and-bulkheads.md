---
title: "Circuit Breakers, Retries & Bulkheads"
---

# Circuit Breakers, Retries & Bulkheads

Circuit breaker states, how a breaker composes with retries and
timeouts, and the bulkhead pattern — the resilience toolkit an API
gateway or any service-to-service caller needs. The basic circuit
breaker state machine is also introduced in
[Fault Tolerance Patterns §1](fault-tolerance-patterns.md#1-circuit-breakers)
alongside retries and graceful degradation; this page goes deeper on
how all three resilience mechanisms interact.

## 1. "Explain circuit breaker states and when each transition happens."

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=30):
        self.state = "closed"
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.opened_at = None

    def call(self, func, *args, **kwargs):
        if self.state == "open":
            if time.monotonic() - self.opened_at > self.recovery_timeout:
                self.state = "half_open"          # let one probe request through
            else:
                raise CircuitOpenError("failing fast, not calling downstream")
        try:
            result = func(*args, **kwargs)
        except Exception:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state, self.opened_at = "open", time.monotonic()
            raise
        else:
            self.state, self.failure_count = "closed", 0   # success resets it
            return result
```

**Answer:** **Closed** is normal operation — calls go through, failures
are counted. Once failures cross a threshold, it trips to **open** —
every call fails immediately without touching the downstream at all
("failing fast"). After a recovery timeout, it moves to **half-open**
and lets a single probe request through: success closes the circuit
again, failure reopens it. The point of failing fast in the open state
is to stop wasting threads, connections, and time waiting on timeouts
to a dependency that's already known to be down — without it, every
caller keeps queuing up behind a slow failure instead of failing
instantly and freeing resources.

## 2. "How does a circuit breaker interact with retries and timeouts — what breaks if you get the order wrong?"

**Answer:** All three solve different problems and have to compose
correctly. A **timeout** bounds how long one call waits. A **retry**
(with backoff and jitter, never a tight loop — see
[Fault Tolerance Patterns §2](fault-tolerance-patterns.md#2-retries-without-making-the-outage-worse))
handles a transient blip. A **circuit breaker** wraps both and stops
trying *at all* once the failure rate shows the dependency is genuinely
down, not just having a bad millisecond. Get the order wrong —
retrying without a circuit breaker, or retrying with no backoff — and a
struggling downstream service gets hit with a **retry storm**: every
failed call spawns more retries, multiplying load on a service that's
already failing, which is exactly the cascading-failure scenario
circuit breakers exist to prevent.

| Pros | Cons / Trade-offs |
|---|---|
| Stops cascading failure from taking down callers of a dead dependency | Adds real complexity — three mechanisms to tune, not one |
| Downstream gets a chance to recover instead of being retried into the ground | A too-sensitive threshold trips on normal transient blips, hurting availability unnecessarily |
| Fast, predictable failure beats a caller hanging on a timeout | Requires per-dependency tuning — one size doesn't fit all backends |

## 3. "What is the bulkhead pattern, and why do you need it alongside a circuit breaker?"

```python
# Each downstream dependency gets its own bounded resource pool --
# a slow payment provider can't starve the connection pool that
# calls the (healthy) inventory service.
payment_pool = ThreadPoolExecutor(max_workers=10)
inventory_pool = ThreadPoolExecutor(max_workers=10)
```

**Answer:** Named after a ship's watertight compartments — a leak in
one doesn't sink the whole vessel. Applied to services, it means giving
each downstream dependency its *own* isolated resource pool (threads,
connections, queue capacity) instead of one shared pool for everything.
A circuit breaker stops you from *calling* a failing dependency once
it's known to be bad; a bulkhead limits the *blast radius* while it's
still degrading but hasn't tripped the breaker yet — without it, a slow
dependency can exhaust a shared thread pool and take down calls to
completely unrelated, healthy dependencies.

---

## Code Samples

No dedicated code samples yet for this page — the `CircuitBreaker`
class above is the same shape shown in
[Fault Tolerance Patterns' Code Samples](fault-tolerance-patterns.md#code-samples)
(`code_samples/chapter-7/fault_tolerance.py`), which already includes a
runnable `Bulkhead` implementation.
