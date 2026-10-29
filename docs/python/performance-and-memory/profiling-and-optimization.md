---
title: "Profiling & Optimization"
---

# Profiling & Optimization

Finding out *where* time actually goes, and fixing it once you know.
This page covers profiling tools and algorithmic optimization
specifically — for the topics that used to live alongside this material
but now have their own real, deeper coverage, see
[Multi-Layer Caching](../../distributed-systems/data-and-capacity-scaling.md#2-multi-layer-caching)
and [Caching Layers & Global Accelerator](../../cloud-devops/caching-layers-and-global-accelerator.md)
for caching, [Load Balancing & Auto-Scaling](../../distributed-systems/load-balancing-and-autoscaling.md)
and [Data & Capacity Scaling](../../distributed-systems/data-and-capacity-scaling.md) for
scaling, [Circuit Breakers, Retries & Bulkheads](../../distributed-systems/circuit-breakers-retries-and-bulkheads.md)
for resilience, and [PostgreSQL for Scale](../../database/postgresql-for-scale.md)
for query diagnosis and index selection.

## 1. "Where do you actually start when someone says an endpoint is slow?"

```python
import cProfile, pstats

def profile(func):
    def wrapper(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()
        result = func(*args, **kwargs)
        pr.disable()
        pstats.Stats(pr).sort_stats("cumulative").print_stats(10)
        return result
    return wrapper
```

**Answer:**

- Profile before guessing. `cProfile` in dev gives function-level timing
  and call counts; sort by cumulative time to find where time is
  actually spent, not where you assume it is.
- In production, `py-spy` attaches to a running process with no code
  changes and near-zero overhead (it samples the stack rather than
  instrumenting every call) — you usually can't drop `cProfile` into a
  live service under real load.

**Likely follow-up — "why not just sprinkle `time.time()` calls
everywhere?"** Doesn't scale past a couple of guesses, and the manual
timing itself adds overhead in different places than the real
bottleneck. A profiler gives you the whole call graph in one pass.

## 2. "How do you track down a memory leak in a long-running Python process?"

```python
import tracemalloc

tracemalloc.start()
snapshot1 = tracemalloc.take_snapshot()
run_workload()
snapshot2 = tracemalloc.take_snapshot()
for stat in snapshot2.compare_to(snapshot1, "lineno")[:10]:
    print(stat)
```

**Answer:**

- `tracemalloc` (built in) gives allocation snapshots you diff over
  time to see which line is responsible for growth; `memory_profiler`
  gives line-by-line usage once you already suspect a specific function.
- In production, watch RSS over time alongside GC stats — steady,
  unbounded growth across GC cycles (not a sawtooth) is the leak
  signature.
- A common real cause is an unbounded in-memory cache that keeps
  everything it's ever seen — see
  [Memory Leaks](../language-fundamentals/python-internals-and-advanced-oop.md#memory-leaks-what-they-actually-are-and-how-one-happens-even-with-a-garbage-collector)
  for the full mechanism and other common Python-specific leak patterns.

## 3. "CPU usage on the box is low but the endpoint is still slow — what's your next move?"

```python
from contextlib import contextmanager
import time

@contextmanager
def timed(label):
    start = time.perf_counter()
    yield
    print(f"{label}: {time.perf_counter() - start:.3f}s")

with timed("db_batch_query"):
    results = await asyncio.gather(*[conn.fetch(q) for q in queries])
```

**Answer:**

- Low CPU with high latency almost always means waiting on I/O —
  database, external API, disk, or network.
- Time each I/O boundary explicitly rather than guessing which one is
  slow; you usually find either N+1 queries, missing connection
  pooling, or sequential calls that should be concurrent.
- The fix is nearly always one of: batch requests instead of one at a
  time, reuse connections (pooling/keep-alive) instead of reconnecting,
  and run independent I/O concurrently instead of awaiting it in
  sequence.

## 4. "What's the difference between profiling and production monitoring, and what do you actually alert on?"

```python
from prometheus_client import Histogram

REQUEST_DURATION = Histogram("request_duration_seconds", "Request duration")

@REQUEST_DURATION.time()
def handle_request(request): ...
```

**Answer:**

- Profiling is a deliberate, point-in-time deep-dive; production
  monitoring runs continuously at near-zero overhead.
- Track the metrics that map to actual user experience — P95/P99
  latency (not just the average, which hides the tail that annoys
  users), error rate, and throughput — and alert on threshold
  violations rather than on every metric that moves. See
  [Prometheus's four metric types](../../distributed-systems/metrics-and-prometheus.md#1-explain-prometheuss-four-metric-types-and-when-youd-reach-for-each)
  and [SLIs and SLOs](../../distributed-systems/metrics-and-prometheus.md#3-design-slis-and-slos-for-an-api-endpoint-how-is-an-slo-different-from-an-sla)
  for the full production-monitoring picture.
- Distributed tracing matters once a single request crosses several
  services, so you can tell which hop actually added the latency
  instead of guessing from aggregate numbers.

## 5. "Give a concrete example where the data structure changed the complexity class, not just the constant factor."

```python
from collections import defaultdict

index: dict[str, set[int]] = defaultdict(set)

def add(doc_id: int, terms: list[str]):
    for term in terms:
        index[term].add(doc_id)

def find(query_terms: list[str]) -> set[int]:
    result = index[query_terms[0]].copy()
    for term in query_terms[1:]:
        result &= index[term]          # set intersection, not nested loops
    return result
```

**Answer:**

- Matching documents against multiple query terms with nested loops is
  O(n·m); indexing by term into a `dict[str, set[int]]` and
  intersecting sets turns lookup-and-match into roughly O(min(set
  sizes)) — a genuinely different complexity class, not just a faster
  constant.
- The same idea generalizes: hash maps for O(1) membership/lookup,
  heaps for O(log n) priority operations instead of re-sorting on every
  insert, and bloom filters when you need a cheap "definitely not
  present" check and can tolerate rare false positives on "maybe
  present."

**Likely follow-up — "when would you avoid a bloom filter?"** When you
need to know exactly what's in the set, or need deletions — a plain
bloom filter doesn't support removal.

## 6. "How do you bound concurrency so 10,000 concurrent requests don't take down the downstream service you're calling?"

```python
semaphore = asyncio.Semaphore(100)

async def fetch(session, url):
    async with semaphore:
        async with session.get(url) as resp:
            return await resp.json()
```

**Answer:**

- `asyncio.gather` with no limit fires everything at once — fine for the
  event loop, not fine for whatever's on the other end.
- A semaphore caps how many requests are in flight at a time regardless
  of how many tasks are queued; pair it with a connection pool that has
  its own limits (`limit`, `limit_per_host`) so you're not opening a
  fresh TCP/TLS handshake per request.
- It's the same shape as "use `asyncio.gather` for concurrent I/O," with
  a backpressure mechanism added once concurrency is high enough that
  the downstream service itself becomes the constraint — see
  [LLM APIs & Providers §4](../../ai-llm/llm-apis-and-providers.md#4-design-an-async-client-for-calling-an-llm-api-under-load-what-does-it-need-beyond-await-clientchatcompletionscreate)
  for this exact pattern applied to a real production client.

| Pros | Cons / Trade-offs |
|---|---|
| Profiling before optimizing avoids fixing the wrong thing entirely | Profiling tools differ between dev (`cProfile`) and production (`py-spy`) — know both |
| A data structure change can shift complexity class, not just speed up a constant factor | Only matters once input size is large enough for the complexity class to dominate |
| A semaphore bounds outgoing concurrency cheaply, in a few lines | Must be paired with connection-pool limits, or you've only solved half the problem |

---

## Code Samples

- `code_samples/chapter-5/profiling_tools.py` — CPU profiling (cProfile), memory profiling (tracemalloc), and I/O timing helpers
- `code_samples/chapter-5/optimization_techniques.py` — data structure selection, algorithmic complexity comparisons, concurrent execution patterns
