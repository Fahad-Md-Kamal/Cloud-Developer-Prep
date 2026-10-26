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

**Answer:** `hash(key) % N` breaks the moment `N` changes — adding one
node to a ten-node cluster to relieve load ends up moving roughly 90%
of the data, the opposite of what you wanted.

- **Why it breaks:** the `% N` in the formula means the node count is
  baked directly into every key's assignment — change `N` by even one,
  and almost every key's result changes too.
- **The fix — consistent hashing:** place both nodes and keys on a
  single ring (a circular range of hash values). Adding or removing a
  node only reassigns the keys sitting in that node's own small slice
  of the ring, not the whole dataset.
- **Why this matters for a shard-per-tenant setup specifically:** it's
  what makes the scheme operationally viable at all — a new tenant
  joining doesn't trigger a cluster-wide reshuffle of everyone else's
  data.

## 2. Multi-Layer Caching

**"You have an edge cache, a regional cache, and the origin database.
Why different TTLs at each layer, not just one cache?"**

**Answer:** Each layer is trading staleness for load reduction at a
different point along the request's path — a cache miss closer to the
user shouldn't mean a trip all the way back to the database.

- **Edge cache (CDN-level)** — shortest TTL. For content that changes
  often but is cheap to refetch, sitting as close to the user as
  possible.
- **Regional cache** — sits closer to your own compute, and can afford
  a somewhat longer TTL than the edge.
- **Origin database** — the actual source of truth, and the layer that
  should see the *least* traffic of all three, since the two caches
  above exist specifically to shield it.
- **The point of tiering:** a miss at the edge cache hits the regional
  cache next, not the database directly — each layer is a buffer for
  the one behind it, not a single flat cache in front of everything.
- **Getting the TTLs wrong shows up immediately, in either direction:**
  too short, and the origin gets hammered with traffic the cache was
  supposed to absorb; too long, and users see stale data with no clear
  way for it to ever get corrected.

## 3. Queue-Based Load Leveling

**"Traffic spikes 10x for two minutes. How does a queue keep that from
taking down the processing tier?"**

```python
await queue.enqueue("document-123")  # accepted immediately, processed at a steady rate
```

**Answer:** A queue absorbs a burst by splitting *accepting* work from
*doing* work, so only the cheap half of that pair has to handle the
spike directly.

- **Accepting work is cheap** — a write to a queue — so the
  producer-facing side can absorb the full 10x spike instantly, with
  no slowdown.
- **Doing the work stays at a steady pace** — a fixed pool of workers
  drains the queue at a sustainable rate, instead of the processing
  tier being forced to instantly scale up 10x to match the spike.
- **The failure mode to design for on purpose: the queue itself backing
  up.** Two concrete guards: a max queue size (so it can't grow forever
  and exhaust memory), and a dead-letter queue for anything that still
  fails after N attempts (so a stuck item doesn't block everything
  behind it).
- **The actual goal of both guards:** a persistent backlog should
  degrade *visibly* — delayed or rejected work you can alert on — not
  grow silently until whatever's serving the queue runs out of memory
  and crashes outright.

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
