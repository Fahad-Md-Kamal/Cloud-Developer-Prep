---
title: "Data & Capacity Scaling"
---

# Data & Capacity Scaling

Sharding without a full rebalance on every node change, tiered caching
with deliberately different TTLs per layer, and queues that absorb
traffic bursts — part of the same distributed-systems discussion as
[Fault Tolerance Patterns](fault-tolerance-patterns.md).

## 1. Sharding Without a Full Rebalance on Every Node Change

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

## 2. Multi-Layer Caching

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

## 3. Queue-Based Load Leveling

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

Runnable examples in `code_samples/chapter-7/` (shared with
[Fault Tolerance Patterns](fault-tolerance-patterns.md) /
[Load Balancing & Auto-Scaling](load-balancing-and-autoscaling.md) /
[Consistency & Consensus](consistency-and-consensus.md)):

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
python code_samples/chapter-7/scaling_strategies.py
python code_samples/chapter-7/integrated_example.py
pytest code_samples/chapter-7/testing_examples.py -q
```
