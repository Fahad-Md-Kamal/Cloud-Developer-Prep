---
title: "DynamoDB & ElastiCache"
---

# DynamoDB & ElastiCache

[AWS Services Quick Reference](aws-services.md#dynamodb) already covers
DynamoDB at the level of "what to say if it comes up." This page goes
deeper, for the exam's actual question style, and adds ElastiCache — the
caching layer DynamoDB's own accelerator (DAX, below) is itself built on
the same idea as.

## DynamoDB: Keys, Indexes & Capacity

- **Partition key** (required) — determines which physical partition an
  item lives on, via a hash. Good key design spreads items evenly across
  partitions; a poorly chosen one (e.g. a status field with only 3
  possible values) creates a **hot partition** that throttles no matter
  how much capacity is provisioned.
- **Sort key** (optional) — combined with the partition key, lets
  multiple items share a partition key and be queried as a range
  (e.g. partition key `userId`, sort key `timestamp`, to fetch a user's
  items in time order).
- **No joins, no schema** beyond the key — this is the trade-off for
  single-digit-millisecond latency at any scale: denormalize the data to
  fit the access pattern, rather than modeling it relationally and
  joining at query time.

### Indexes: Querying by Something Other Than the Primary Key

`Local Secondary Index (LSI)`
:   Same partition key as the base table, a different sort key. Must be
    created **at table creation time**, and shares the base table's
    capacity.

`Global Secondary Index (GSI)`
:   A different partition key (and optionally sort key) entirely —
    effectively a second table, automatically kept in sync. Can be added
    **at any time**, and has its own provisioned/on-demand capacity,
    independent of the base table's.

!!! success "The exam signal"

    "Need to query by an attribute that isn't the partition key, decided
    after the table already exists" → GSI, since an LSI can only be
    added at creation time. This single fact is why GSIs are the
    overwhelmingly more common answer on the exam.

### Capacity Modes

| | On-Demand | Provisioned |
|---|---|---|
| You specify | Nothing — scales automatically | Read/write capacity units ahead of time |
| Cost model | Pay per request | Pay for provisioned capacity, whether used or not |
| Best for | Unpredictable or spiky traffic, new workloads with unknown patterns | Steady, predictable traffic where you can forecast capacity and want the lower cost of reserving it |

### DAX — DynamoDB Accelerator

An in-memory cache sitting directly in front of DynamoDB, purpose-built
for it — reduces read latency from single-digit milliseconds to
microseconds for repeated reads.

- Fully managed, API-compatible with the DynamoDB SDK — minimal code
  change to add it.
- Caches both individual item lookups (`GetItem`) and query results.
- Only helps **read-heavy** workloads; writes always go to DynamoDB
  itself (write-through), DAX doesn't reduce write latency.

### Global Tables

Multi-region, **multi-active** replication for DynamoDB — every replica
in every region accepts both reads and writes, with changes propagating
to all other regions automatically.

- Different from Aurora Global Database's model (one writer region,
  others read-only) — DynamoDB Global Tables accept writes
  **everywhere**, and use last-writer-wins conflict resolution for
  concurrent writes to the same item.

!!! success "The exam signal"

    "Active-active, multi-region application, users write from multiple
    regions simultaneously" → DynamoDB Global Tables. If the question
    needs a single authoritative writer with regional read replicas
    instead, that's
    [Aurora Global Database](aurora-and-rds-proxy.md#aurora-global-database),
    not this.

## ElastiCache: Redis vs Memcached

A managed in-memory cache sitting in front of a (usually relational)
database — the general-purpose version of what DAX does specifically
for DynamoDB.

| | Redis | Memcached |
|---|---|---|
| Data structures | Rich — strings, lists, sets, sorted sets, hashes | Simple key-value only |
| Persistence | Yes — can survive a restart | No — purely in-memory, gone on restart |
| Replication / Multi-AZ | Yes | No |
| Clustering | Yes (sharding across nodes) | Yes (simpler, just distributes keys) |
| Multi-threading | Single-threaded per node (until recent versions) | Multi-threaded |
| Use for | Needs persistence, replication, pub/sub, leaderboards (sorted sets), or any structure beyond plain key-value | Pure, simple, multi-threaded caching, horizontally scaled, nothing needs to survive a restart |

!!! success "The exam signal"

    "Needs the cache to survive a failover / be highly available" →
    Redis, since Memcached has no replication at all. "Simplest possible
    cache, needs to scale horizontally across many simple threads" →
    Memcached. A question mentioning leaderboards, pub/sub, or any
    non-trivial data structure → Redis, always.
