---
title: "Redis as a Database"
---

# Redis as a Database

Redis already shows up on this site as a cache (see
[Caching Layers & Global Accelerator](../cloud-devops/caching-layers-and-global-accelerator.md)).
This page covers what gets left out of that framing: Redis has
persistence, rich data structures beyond a flat key-value pair, and real
production systems where it's the primary store, not a layer in front of
one. The mechanism underneath it explains both roles at once.

## 1. "Why is Redis so fast — what's actually happening under the hood?"

**Answer:**

- Everything lives in RAM — no disk seek on the read/write path at all,
  which alone accounts for most of the speed difference versus a
  disk-backed database.
- Operations run against purpose-built data structures (hashes, sorted
  sets, lists, sets) chosen specifically so the common operation on each
  one is O(1) or O(log n) — there's no general-purpose query planner
  deciding how to execute an arbitrary query, because Redis doesn't have
  one; you pick the data structure that already matches your access
  pattern.
- It's **single-threaded** for command execution — only one command runs
  at a time on the core data — which sounds like it should be slow, but
  actually removes the cost of lock contention entirely: there's never a
  need to coordinate between threads fighting over the same key, because
  there's only ever one thread touching it.

## 2. "If it's single-threaded, how does it handle many concurrent clients at all?"

**Answer:**

- Through an **event loop** built on I/O multiplexing (`epoll` on
  Linux) — the exact same OS-level mechanism already explained in
  [AsyncIO Internals](../backend/python/asyncio-internals.md#the-os-io-model-underneath-asyncio):
  one thread asks the kernel "which of these thousands of sockets
  actually has data ready," instead of checking each one individually or
  dedicating a thread per connection.
- Redis's single thread handles the actual command execution; a small
  number of background threads handle slower operations (persistence
  writes, large key deletion) so those don't block the main loop.
- The practical consequence: Redis serves a huge number of concurrent
  clients well, as long as no single command is slow — a single
  expensive command (an unbounded `KEYS *` scan, a huge sorted-set
  operation) blocks every other client's request until it finishes,
  because there's genuinely only one thread doing the work.

## 3. "What happens to data when Redis restarts — is it really 'just a cache' if it has persistence?"

**Answer:**

- **RDB (snapshotting)** — periodically dumps the entire dataset to disk
  as a single binary file. Fast to restart from, but any writes since the
  last snapshot are lost on a crash.
- **AOF (Append-Only File)** — logs every write operation to disk as it
  happens, replayed in order on restart to rebuild the exact state —
  the same durability idea as a
  [write-ahead log](postgresql-for-scale.md#the-write-ahead-log-wal-durability-and-crash-recovery),
  trading some write throughput for much better durability than RDB
  alone.
- Most production deployments run both together — RDB for fast,
  compact full-dataset snapshots, AOF for minimizing data loss between
  them — which is exactly the point where "Redis as a cache" (ephemeral,
  fine to lose) and "Redis as a database" (needs to survive a restart)
  actually diverge as configuration choices, not different products.

## 4. "What's a sorted set, and why is it worth knowing as its own data structure?"

**Answer:**

- A collection of members, each with an associated numeric **score**,
  kept in score order automatically — backed internally by a skip list,
  giving O(log n) insertion and O(log n) range queries by score.
- This single structure covers a surprising number of real production
  use cases directly: a **leaderboard** (score = points, member =
  player), a **rate limiter** (score = timestamp, trimming anything
  older than the current window), and a **priority queue** (score =
  priority or scheduled time).
- Knowing this one data structure well is usually a better interview
  signal than reciting Redis's full command list — it shows you
  understand *why* Redis fits a use case, not just that you've used it.

## 5. "When is Redis the primary store, not just a cache in front of Postgres?"

**Answer:**

- When the data is genuinely **ephemeral by nature** — a user session, a
  real-time leaderboard, a rate limiter's counters — there's no "source
  of truth" elsewhere to fall back to, because this *is* the source of
  truth for that specific, narrow piece of state.
- When the access pattern is purely key-based or structure-based (sorted
  sets, hashes) with no need for joins, and AOF persistence gives
  durability good enough for the use case.
- **Pub/sub messaging** — Redis's publish/subscribe feature makes it a
  lightweight message broker for real-time notifications, independent of
  whether it's also being used as a cache or store elsewhere in the same
  system.
- The line not to cross: anything needing multi-row transactions,
  complex relational queries, or long-term durability guarantees beyond
  what AOF provides still belongs in a relational or document store —
  Redis earns the "primary store" role for narrow, structure-matched
  data, not as a general replacement for one.

| Pros | Cons / Trade-offs |
|---|---|
| In-memory + purpose-built data structures make it extremely fast for matched access patterns | Dataset size is bounded by available RAM — not built for data larger than memory |
| AOF persistence gives real durability, not just a volatile cache | Single-threaded execution means one slow command blocks every other client |
| Sorted sets alone cover leaderboards, rate limiting, and priority queues with one structure | No joins, no relational query language — wrong fit for complex relational data |
| Pub/sub gives lightweight real-time messaging in the same system already running the cache | Not a system of record for data that needs long-term, large-scale durable storage |

---

## Code Samples

No dedicated code samples for this page.
