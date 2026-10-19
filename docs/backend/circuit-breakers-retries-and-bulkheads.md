---
title: "Circuit Breakers, Retries & Bulkheads"
---

# Circuit Breakers, Retries & Bulkheads

How a circuit breaker composes with retries and timeouts, and the
bulkhead pattern — the resilience toolkit an API gateway or any
service-to-service caller needs. The circuit breaker state machine
itself, with the electrical-panel analogy behind it, is covered in
[Fault Tolerance Patterns §1](fault-tolerance-patterns.md#1-circuit-breakers);
this page assumes that and goes deeper on how it actually combines with
the other two mechanisms.

## 1. Circuit Breaker States, Briefly

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

**Answer:** closed (normal, failures counted) → open (fail fast, no
downstream call at all, for `recovery_timeout` seconds) → half-open
(one probe call; success closes it, failure reopens it). Failing fast
in the open state exists to free up threads/connections immediately
instead of letting every caller queue up behind a slow timeout to a
dependency that's already known to be down. See
[Fault Tolerance Patterns §1](fault-tolerance-patterns.md#1-circuit-breakers)
for the full walkthrough and the electrical-breaker analogy it's named
after.

## 2. "How does a circuit breaker interact with retries and timeouts — what breaks if you get the order wrong?"

**Answer:** All three solve a different problem, and they only work
together if they compose in the right order.

- **A timeout** bounds how long a *single* call is allowed to wait.
- **A retry** (with backoff and jitter — never a tight loop; see
  [Fault Tolerance Patterns §2](fault-tolerance-patterns.md#2-retries-without-making-the-outage-worse))
  handles a short, transient blip.
- **A circuit breaker** wraps both of those, and stops trying *at all*
  once the failure rate shows the dependency is genuinely down — not
  just having one bad millisecond.
- **Get the order wrong** — retrying without a circuit breaker, or
  retrying with no backoff at all — and a struggling downstream service
  gets hit by a **retry storm**: every failed call spawns more retries,
  multiplying load on a service that's already failing. That's the
  exact cascading-failure scenario circuit breakers exist to prevent.

| Pros | Cons / Trade-offs |
|---|---|
| Stops cascading failure from taking down callers of a dead dependency | Adds real complexity — three mechanisms to tune, not one |
| Downstream gets a chance to recover instead of being retried into the ground | A too-sensitive threshold trips on normal transient blips, hurting availability unnecessarily |
| Fast, predictable failure beats a caller hanging on a timeout | Requires per-dependency tuning — one size doesn't fit all backends |

## 3. "What is the bulkhead pattern, and why do you need it alongside a circuit breaker?"

!!! example "Real-world analogy: a ship's watertight compartments"
    - A ship's hull is divided into separate, sealed compartments. A
      leak in one compartment floods *that* compartment — the
      watertight walls keep the water from spreading and sinking the
      whole ship.
    - Applied to services: give each downstream dependency its **own**
      isolated resource pool (threads, connections, queue capacity)
      instead of one shared pool for everything. A dependency that's
      struggling can only exhaust *its own* pool, not everyone else's.

```python
# Each downstream dependency gets its own bounded resource pool --
# a slow payment provider can't starve the connection pool that
# calls the (healthy) inventory service.
payment_pool = ThreadPoolExecutor(max_workers=10)
inventory_pool = ThreadPoolExecutor(max_workers=10)
```

**Answer:**

- A circuit breaker stops you from **calling** a dependency once it's
  already known to be bad.
- A bulkhead limits the **blast radius** while a dependency is still
  degrading but hasn't tripped the breaker yet.
- Without a bulkhead, a single slow dependency sharing a resource pool
  with everything else can exhaust that shared pool — and take down
  calls to completely unrelated, perfectly healthy dependencies along
  with it.

---

## Code Samples

No dedicated code samples yet for this page — the `CircuitBreaker`
class above is the same shape shown in
[Fault Tolerance Patterns' Code Samples](fault-tolerance-patterns.md#code-samples)
(`code_samples/chapter-7/fault_tolerance.py`), which already includes a
runnable `Bulkhead` implementation.
