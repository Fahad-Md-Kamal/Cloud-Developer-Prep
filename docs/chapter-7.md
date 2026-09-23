---
title: "Chapter 7: Distributed System Design (Fault Tolerance, Load Balancing, Scaling)"
---

# Chapter 7: Distributed System Design (Fault Tolerance, Load Balancing, Scaling)

Fault tolerance, load balancing, consistency/consensus, and scaling
patterns for systems that span multiple machines and can't assume
anything stays up — as questions you should be able to answer cold,
code plus the trade-off, not just the upside.

---

## Part 1: Fault Tolerance

### 1. Circuit Breakers

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

### 2. Retries Without Making the Outage Worse

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

### 3. Graceful Degradation

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

## Part 2: Load Balancing and Auto-Scaling

### 4. Choosing a Load-Balancing Algorithm

**"Round-robin, weighted round-robin, least-connections — how do you
pick?"**

```python
class LeastConnectionsBalancer:
    def select(self, backends: list[Backend]) -> Backend:
        return min(backends, key=lambda b: b.active_connections)
```

**Answer:** Plain round-robin assumes every backend and every request is
equivalent — fine for uniform, short-lived requests across identical
instances. Weighted round-robin biases traffic toward higher-capacity or
lower-latency replicas when instances *aren't* identical (mixed
instance sizes, multi-region with different latencies). Least
connections is the right call when requests vary a lot in processing
time — a backend stuck on a few slow requests stops receiving new ones,
instead of round-robin blindly sending it a fifth request while three
others sit idle. Session affinity (sticky sessions) is a separate axis,
needed only when a service actually holds per-user state in-process —
it should carry an expiry, or affinity to a since-replaced instance
quietly breaks.

**Likely follow-up — "what's the risk with sticky sessions at scale?"**
Hot shards — if the hash used for affinity isn't well distributed, some
instances end up disproportionately loaded while others sit idle, and
you lose the main benefit of load balancing in the first place.

### 5. Auto-Scaling on the Right Signal

**"CPU usage looks fine but the service is falling behind. What went
wrong with the scaling policy?"**

**Answer:** CPU is a lagging, often misleading signal for I/O-bound or
queue-backed services — a service can be CPU-idle while every request
sits waiting on a downstream call or a queue drains too slowly.
Multi-metric scaling (P95/P99 latency, error rate, and — for anything
backed by a queue — queue depth or consumer lag) reacts to the thing
that actually matters to users. Queue lag in particular is a leading
indicator: it rises well before latency does, giving auto-scaling time
to add capacity before requests start timing out instead of reacting
after they already have.

---

## Part 3: Consistency and Consensus

### 6. Picking a Consistency Model Per Use Case

**"Does everything in a distributed system need to be strongly
consistent?"**

```python
event_log.append(Event(aggregate_id="doc-541", type="CLASSIFIED", payload={"tag": "Tax"}))
for event in event_log.replay():
    read_model.apply(event)  # projection can lag; rebuildable from the log
```

**Answer:** No — and treating everything as if it did is how systems
end up needlessly slow and coupled. Strong consistency earns its cost
where a stale read causes real harm (a balance, an inventory count,
anything billing touches). Everything else — a dashboard, a search
index, an activity feed — is a legitimate candidate for eventual
consistency via **event sourcing**: business events are appended to an
immutable log, and **read models** (projections) are derived from it
asynchronously. The read model can lag, but it's cheap to rebuild from
the log from scratch, which doubles as a disaster-recovery story —
replay the log instead of trying to repair corrupted derived state
directly.

| Pros | Cons / Trade-offs |
|---|---|
| Read models can lag without threatening correctness of the source of truth | Consumers must handle out-of-order/duplicate events — idempotency isn't optional |
| Rebuilding a projection from the log is a real recovery mechanism, not just a backup | The event log itself must never be lossy — it's now the actual source of truth |
| Full audit trail of every state change, for free | Querying "current state" directly against a log is awkward — you need the projection anyway |

### 7. When You Actually Need Consensus

**"When do you reach for a consensus protocol (Raft/Paxos) instead of
just eventual consistency?"**

**Answer:** When multiple nodes must agree on a single value and
*disagreeing* is unacceptable — leader election, a config/feature-flag
change that must not apply inconsistently across regions, or a schema
migration gate. You rarely implement Raft yourself; you rely on
something built on it (etcd, Zookeeper, Spanner, a managed consensus
service) and reason about the trade-off it exposes: a quorum (e.g., 2 of
3 nodes) tolerates the minority failing, at the cost of every write
needing a round trip to a majority of nodes — more latency than a
single node ever needs, in exchange for surviving a node failure without
split-brain.

---

## Part 4: Data and Capacity Scaling

### 8. Sharding Without a Full Rebalance on Every Node Change

**"You add a node to a sharded cluster. What happens to the existing
data if you sharded with `hash(key) % N`?"**

```python
# Naive: adding a node changes N, remaps almost every key
shard = hash(tenant_id) % node_count

# Consistent hashing: adding/removing a node only remaps its own slice
ring = ConsistentHashRing(nodes)
shard = ring.get_node(tenant_id)
```

**Answer:** `hash(key) % N` remaps nearly *every* key the moment `N`
changes — adding one node to a ten-node cluster to relieve load ends up
moving roughly 90% of the data, the opposite of what you wanted.
Consistent hashing places both nodes and keys on a ring, so adding or
removing a node only reassigns the keys in its immediate neighborhood —
a small, bounded fraction of the total. This is also what keeps a
shard-per-tenant scheme operationally viable: a new tenant doesn't
trigger a cluster-wide reshuffle.

### 9. Multi-Layer Caching

**"You have an edge cache, a regional cache, and the origin database.
Why different TTLs at each layer, not just one cache?"**

**Answer:** Each layer trades staleness for load reduction at a
different point in the request path. Edge caches (CDN-level) use the
shortest TTLs for content that changes often but is cheap to refetch;
regional caches sit closer to compute and can afford slightly longer
TTLs; the origin database is the source of truth and should see the
least traffic of all. Tiering means a cache miss at the edge doesn't
necessarily hit the database — it hits the regional cache first.
Getting this wrong in either direction shows up immediately: TTLs too
short and the origin gets hammered; too long and users see stale data
with no clear invalidation path.

### 10. Queue-Based Load Leveling

**"Traffic spikes 10x for two minutes. How does a queue keep that from
taking down the processing tier?"**

```python
await queue.enqueue("document-123")  # accepted immediately, processed at a steady rate
```

**Answer:** The queue absorbs the burst by decoupling *acceptance* of
work from *processing* of work — the producer-facing side accepts the
spike instantly (a write to a queue is cheap), while a fixed pool of
workers drains it at a steady, sustainable rate instead of the
processing tier trying to instantaneously scale 10x. The failure mode
to design for explicitly is the queue itself backing up: a max queue
size plus a dead-letter queue for anything that can't be processed
after N attempts, so a persistent backlog degrades visibly
(rejected/delayed work, alertable) instead of growing unbounded until
whatever's serving the queue runs out of memory.

| Pros | Cons / Trade-offs |
|---|---|
| Producer-side latency stays flat even during a burst | Adds end-to-end processing latency — not appropriate for anything needing an immediate response |
| Processing capacity can be sized for average load, not peak | Queue depth becomes a new failure mode that needs its own monitoring and alerting |
| A backlog is visible and recoverable, not silently dropped requests | Requires idempotent processing — a crashed worker means a message gets redelivered |

---

## Code Samples

Runnable examples in `code_samples/chapter-7/`:

- `fault_tolerance.py` — `CircuitBreaker`, `Bulkhead`,
  `retry_with_backoff`, `graceful_degradation`
- `load_balancing.py` — `WeightedRoundRobin`, `LeastConnectionsBalancer`,
  `GeoRouter`, `TrafficScaler`
- `consistency_strategies.py` — `EventLog`/`ReadModel` (event sourcing +
  projection) and a `ConsensusCoordinator` (quorum voting)
- `scaling_strategies.py` — `CapacityPlanner`, `ShardingManager`,
  `CacheOrchestrator`, `QueueLoadLeveler`
- `integrated_example.py` — routes a request through a load balancer and
  a circuit breaker together, end to end
- `testing_examples.py` — pytest suite covering breaker state
  transitions, load-balancer fairness, and shard distribution
- `resilience-config.yaml` — externalized thresholds (breaker,
  autoscaling, quorum, retry/cache defaults) referenced by the above

```bash
pip install -r code_samples/chapter-7/requirements.txt
python code_samples/chapter-7/fault_tolerance.py
python code_samples/chapter-7/load_balancing.py
python code_samples/chapter-7/scaling_strategies.py
python code_samples/chapter-7/integrated_example.py
pytest code_samples/chapter-7/testing_examples.py -q
```

---

## Summary

1. **Fault tolerance** is layered — bulkheads limit blast radius,
   circuit breakers stop calling a dependency that's already failing,
   backoff+jitter keeps retries from becoming the next outage, and
   graceful degradation defines the fallback tier in advance instead of
   improvising one.
2. **Load balancing** algorithm choice follows from whether backends and
   requests are actually uniform; auto-scaling needs to react to the
   metric that reflects real user impact (latency, errors, queue lag),
   not just CPU.
3. **Consistency** is a per-use-case decision — strong where staleness
   causes real harm, eventual (via event sourcing/read models)
   everywhere else; real consensus protocols are for the narrow case
   where nodes must agree and disagreement is unacceptable.
4. **Scaling data** means consistent hashing for sharding, tiered
   caching with deliberately different TTLs per layer, and queues that
   absorb bursts while making backlog a visible, alertable condition
   instead of a silent failure.
