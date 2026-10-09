---
title: "Fault Tolerance Patterns"
---

# Fault Tolerance Patterns

Circuit breakers, retries without making an outage worse, and graceful
degradation — the three patterns that stop one failing dependency from
taking the rest of the system down with it. A fuller circuit-breaker
treatment, including its interaction with timeouts and bulkheads, lives
in [Circuit Breakers, Retries & Bulkheads](circuit-breakers-retries-and-bulkheads.md).

## 1. Circuit Breakers

**"Design a circuit breaker for a flaky downstream dependency. Walk
through its states."**

```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int, recovery_timeout: float):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.state = "closed"
        self.opened_at: float | None = None

    def call(self, func, *args):
        if self.state == "open":
            if time.monotonic() - self.opened_at < self.recovery_timeout:
                raise CircuitOpenError()
            self.state = "half_open"  # let one probe through
        try:
            result = func(*args)
        except Exception:
            self.failures += 1
            if self.failures >= self.failure_threshold:
                self.state, self.opened_at = "open", time.monotonic()
            raise
        else:
            self.failures, self.state = 0, "closed"
            return result
```

**Answer:** Three states. **Closed** — calls go through normally,
failures are counted. **Open** — once failures cross the threshold,
calls fail fast without even attempting the downstream call, for
`recovery_timeout` seconds; this is what protects the caller's own
thread/connection pool from piling up waiting on a dependency that's
already down. **Half-open** — after the timeout, exactly one probe call
is let through; success resets to closed, failure reopens the breaker.
The point isn't retrying smarter — it's refusing to call at all once a
dependency has proven itself unhealthy, so one failing dependency can't
exhaust the resources every *other* request also needs.

**Likely follow-up — "how is a bulkhead different from this?"** A
circuit breaker decides *whether* to call a dependency at all; a
bulkhead limits *how much concurrency* any one dependency can consume
regardless of whether it's healthy — a fixed-size worker pool or
semaphore per dependency, so a slow (but not yet failing) call to
service A can't starve out the threads service B's calls need. They
compose: the bulkhead limits blast radius while the breaker is still
closed, the breaker stops the bleeding once it's clearly not helping.
See [Circuit Breakers, Retries & Bulkheads §3](circuit-breakers-retries-and-bulkheads.md#3-what-is-the-bulkhead-pattern-and-why-do-you-need-it-alongside-a-circuit-breaker)
for the full bulkhead treatment.

## 2. Retries Without Making the Outage Worse

**"What goes wrong if every client retries a failing call with a fixed
delay?"**

```python
def retry_with_backoff(func, attempts=3, base_delay=0.1):
    for attempt in range(attempts):
        try:
            return func()
        except Exception:
            if attempt == attempts - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, base_delay)
            time.sleep(delay)  # exponential backoff + jitter
```

**Answer:** A fixed retry delay means every client that failed at the
same moment retries at the same moment again — a thundering herd that
can turn a brief blip into a sustained outage, since the retry wave
itself becomes the load spiking the still-recovering service.
Exponential backoff spreads retries out over time; adding jitter
(randomizing the delay) spreads them across clients too, so they don't
re-synchronize on every attempt. Retries should also be
circuit-breaker-aware — retrying against a breaker that's already open
just wastes the wait; fail fast instead.

## 3. Graceful Degradation

**"A recommendation service times out. What's the actual fallback, not
just 'show an error'?"**

```python
result = graceful_degradation(
    primary=lambda: fetch_live_recommendations(user_id),
    fallback=lambda exc: fetch_cached_recommendations(user_id),  # last-known-good
)
```

**Answer:** Define the degraded experience explicitly as a tier, not as
an afterthought — fresh data, then cached/last-known-good data, then a
static default, each one a real, previously-decided fallback rather
than an exception handler improvised at 2am. The point is that a
dependency failing should shrink the *quality* of the response, not the
*availability* of the whole page. Whichever tier serves the response,
log that a degradation happened — customers not noticing is the goal,
engineers not noticing is a problem.

| Pros | Cons / Trade-offs |
|---|---|
| Users get a usable (if stale) response instead of an error page | Serving stale/cached data can itself be wrong for some use cases (pricing, inventory) |
| Buys time for the dependency to recover without paging anyone at 2am | Every tier is more code paths to test and keep working |
| Degradation events are measurable — a leading indicator, not just an outage postmortem | Easy to let a "temporary" fallback quietly become permanent |

---

## Code Samples

Runnable examples in `code_samples/chapter-7/` (shared with
[Load Balancing & Auto-Scaling](load-balancing-and-autoscaling.md) /
[Consistency & Consensus](consistency-and-consensus.md) /
[Data & Capacity Scaling](data-and-capacity-scaling.md)):

- `fault_tolerance.py` — `CircuitBreaker`, `Bulkhead`,
  `retry_with_backoff`, `graceful_degradation`

```bash
pip install -r code_samples/chapter-7/requirements.txt
python code_samples/chapter-7/fault_tolerance.py
```
