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

!!! example "Real-world analogy: the breaker in your electrical panel"
    - A real circuit breaker protects your house's wiring: if a circuit
      draws too much current, the breaker trips and cuts power to that
      circuit, rather than letting the wiring overheat.
    - A software circuit breaker does the same job for a failing
      dependency: once it's clearly unhealthy, stop sending it calls,
      rather than letting every request pile up waiting on something
      that's already broken.
    - A real breaker doesn't stay off forever, either — eventually you
      flip it back on to see if the problem's gone. That's the
      "half-open" state below.

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

**Answer:** Three states, and the point of all three together is:
refuse to call a dependency at all once it's proven itself unhealthy,
so one failing dependency can't exhaust the resources every *other*
request also needs — this isn't about retrying smarter, it's about
stopping.

- **Closed** — normal operation. Calls go through, and failures are
  counted.
- **Open** — once failures cross the threshold, calls fail
  *immediately*, without even attempting the downstream call, for
  `recovery_timeout` seconds. This is what actually protects the
  caller: its own threads/connections never pile up waiting on a
  dependency that's already down.
- **Half-open** — once the timeout passes, exactly *one* probe call is
  let through to test the water. Success resets the breaker to closed;
  failure sends it straight back to open.

**Likely follow-up — "how is a bulkhead different from this?"**

- A circuit breaker decides **whether to call a dependency at all**.
- A bulkhead limits **how much concurrency any one dependency can
  consume**, whether or not it's currently healthy — a fixed-size
  worker pool or semaphore per dependency, so a slow (but not yet
  failing) call to service A can't starve out the threads service B's
  calls need.
- They work together: the bulkhead limits the blast radius while the
  breaker is still closed; the breaker stops the bleeding entirely once
  it's clear the dependency isn't helping anymore. See
  [Circuit Breakers, Retries & Bulkheads §3](circuit-breakers-retries-and-bulkheads.md#3-what-is-the-bulkhead-pattern-and-why-do-you-need-it-alongside-a-circuit-breaker)
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

**Answer:** A fixed delay means every client that failed at the same
moment also retries at the same moment — a **thundering herd**. That
retry wave becomes a fresh spike of load hitting a service that's still
trying to recover, and can turn a brief blip into a sustained outage.

- **Exponential backoff** — each retry waits longer than the last
  (`base_delay * 2^attempt`), spreading retries out over time instead
  of firing them all at once.
- **Jitter** — add a small random amount to each delay, so different
  clients don't stay in lockstep with each other on every retry
  (without jitter, "wait twice as long" still has every client waiting
  the *same* "twice as long," and they all pile up together again).
- **Circuit-breaker-aware retries** — don't retry against a breaker
  that's already open. The breaker has already decided the dependency
  is down; retrying anyway just wastes the wait instead of failing
  fast.

## 3. Graceful Degradation

**"A recommendation service times out. What's the actual fallback, not
just 'show an error'?"**

```python
result = graceful_degradation(
    primary=lambda: fetch_live_recommendations(user_id),
    fallback=lambda exc: fetch_cached_recommendations(user_id),  # last-known-good
)
```

**Answer:** A dependency failing should shrink the *quality* of the
response, not the *availability* of the whole page.

- Define the degraded experience as explicit **tiers**, decided ahead
  of time — fresh data, then cached/last-known-good data, then a
  static default — not an exception handler improvised during an
  incident at 2am.
- Each tier is a real, previously-tested fallback, not a guess made
  under pressure while something is already on fire.
- Whichever tier actually served the response, **log that a
  degradation happened**. The goal is customers not noticing; engineers
  not noticing is the actual problem.

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
