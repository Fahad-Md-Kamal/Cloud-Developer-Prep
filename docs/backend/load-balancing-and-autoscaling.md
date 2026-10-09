---
title: "Load Balancing & Auto-Scaling"
---

# Load Balancing & Auto-Scaling

Choosing a load-balancing algorithm, and scaling on the signal that
actually reflects user impact instead of a misleading one — part of the
same distributed-systems discussion as
[Fault Tolerance Patterns](fault-tolerance-patterns.md).

## 1. Choosing a Load-Balancing Algorithm

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

## 2. Auto-Scaling on the Right Signal

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

## Code Samples

Runnable examples in `code_samples/chapter-7/` (shared with
[Fault Tolerance Patterns](fault-tolerance-patterns.md) /
[Consistency & Consensus](consistency-and-consensus.md) /
[Data & Capacity Scaling](data-and-capacity-scaling.md)):

- `load_balancing.py` — `WeightedRoundRobin`, `LeastConnectionsBalancer`,
  `GeoRouter`, `TrafficScaler`

```bash
pip install -r code_samples/chapter-7/requirements.txt
python code_samples/chapter-7/load_balancing.py
```
