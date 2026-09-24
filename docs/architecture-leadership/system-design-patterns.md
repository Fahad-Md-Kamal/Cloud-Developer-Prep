---
title: "Common System Design Patterns"
---

# Common System Design Patterns

Load balancing, caching, sharding/replication, message queues, and
CDNs — the recurring building blocks system design interviews expect
fluency in. Most of these have their own deep-dive page already; this
page is the interview-framing layer, not a re-derivation.

## 1. "How do you choose a load-balancing strategy?"

**Answer:**

- **Round robin** — simplest, works well when requests are roughly
  uniform cost and backend instances are roughly equal capacity.
- **Least connections** — routes to whichever backend currently has
  the fewest active connections; better than round robin when request
  cost varies a lot.
- **Consistent hashing** — routes the same key (e.g. a user ID) to the
  same backend consistently, which matters when that backend is
  caching per-key state locally and a cache miss on every request
  would be expensive.
- **L4 vs. L7**: L4 (transport layer) balances raw TCP connections,
  cheaper and protocol-agnostic; L7 (application layer) can route on
  actual request content (path, header, cookie), enabling smarter
  routing at the cost of more processing per request.

## 2. "How do you decide on a caching strategy for a system design answer?"

**Answer:**

- Identify what's actually expensive to (re)compute or fetch — caching
  something cheap adds complexity for no real benefit.
- **Cache-aside** (read: check cache, miss → read DB → populate cache)
  is the default pattern for read-heavy, tolerant-of-slight-staleness
  data.
- **Write-through** (every write updates the cache and the DB
  together) keeps the cache always consistent, at the cost of every
  write paying the cache-update cost too.
- Invalidation strategy matters as much as the caching pattern itself
  — TTL-based (simple, bounded staleness) vs. event-based (precise,
  more moving parts). See
  [Memory & Caching](../programming-languages/python/memory-and-caching.md)
  for the mechanics at the single-process level, and
  [LLM Response Caching](../ai-llm/llm-response-caching.md) for a
  worked TTL-strategy example that generalizes beyond LLM responses.

## 3. "How do you talk about sharding and replication in a system design answer?"

**Answer:**

- Replication buys read scaling and availability; sharding buys write
  scaling by partitioning data across machines. They solve different
  problems and are often used together, not as alternatives to each
  other.
- The shard key choice is the actual design decision worth spending
  interview time on — a poorly chosen key creates a hot shard that
  defeats the point. See
  [MongoDB for Scale §3](../data-and-engineering/mongodb-for-scale.md#3-how-does-mongodb-scale-writes-and-reads-and-how-do-you-pick-a-shard-key)
  for the concrete mechanics.
- For a relational store specifically, see
  [PostgreSQL for Scale](../data-and-engineering/postgresql-for-scale.md)
  for replication's synchronous/asynchronous trade-off and
  partitioning.

## 4. "How do message queues and event-driven patterns fit into a system design answer?"

**Answer:**

- Reach for a queue when work can happen asynchronously relative to
  the request that triggered it, or when producer and consumer need
  to scale independently.
- The interview-level judgment call is usually "synchronous call vs.
  queue," not picking a specific broker — be ready to justify why a
  given interaction needs to be async at all.
- For the concrete choice between message brokers and the patterns
  built on top of them (sagas, schema evolution), see
  [Chapter 6: Microservices & Message Queues](../backend-architecture/chapter-6.md)
  and [Chapter 27: Event-Driven Architectures](chapter-27.md).

## 5. "When does a CDN or edge computing actually matter for a design?"

**Answer:**

- A CDN matters once **geographic latency** is a real constraint — a
  global user base hitting an origin server on another continent pays
  real round-trip cost that no amount of origin-side optimization
  fixes.
- Static/cacheable content (images, video, static assets, and
  increasingly cacheable API responses) is the natural fit; anything
  highly personalized or write-heavy generally isn't.
- Edge computing (running actual logic at CDN edge nodes, not just
  caching) is worth mentioning as the natural next step when a design
  needs computation close to the user, not just cached content — but
  it's a genuinely newer, less universally-applicable pattern than
  CDN caching itself, worth flagging as such rather than reaching for
  it by default.
