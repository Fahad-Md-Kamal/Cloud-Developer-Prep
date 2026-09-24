---
title: "Cross-Store Architecture Patterns"
---

# Cross-Store Architecture Patterns

CQRS, database-per-microservice, and keeping two databases in sync —
the patterns that show up once a system uses more than one data store
and has to reason about consistency across them. Builds on
[PostgreSQL for Scale](postgresql-for-scale.md),
[MongoDB for Scale](mongodb-for-scale.md), and
[Elasticsearch Architecture](elasticsearch-architecture.md).

## 1. "When would you reach for CQRS — separate read and write models?"

**Answer:**

- Reach for it when the shape that makes writes consistent (a
  normalized relational schema, wrapped in transactions) is a bad fit
  for how reads actually query the data (denormalized, aggregated,
  full-text).
- CQRS keeps the write side optimized for correctness and the read
  side optimized for the query patterns the application actually
  needs — often a different store entirely (a read replica, a
  denormalized Mongo collection, or an Elasticsearch index), kept in
  sync via events or change data capture.
- The cost is real: the read side is now eventually consistent with
  the write side, and there's more infrastructure (the sync mechanism
  itself) that can fail or lag.

| Pros | Cons / Trade-offs |
|---|---|
| Read side can be denormalized exactly to match real query patterns | Read/write models must be kept in sync — eventual consistency, not immediate |
| Write side stays simple/normalized/transactional | More infrastructure: the sync pipeline is a new thing that can break or lag |
| Read and write sides can scale independently | Debugging "why does the read side show stale data" is a new failure mode |

## 2. "Database-per-microservice — what does it actually buy you, and what does it cost?"

**Answer:**

- It buys genuine service independence: each service evolves its own
  schema and deploys on its own schedule, and no other service can
  accidentally couple itself to your internal tables (the failure mode
  of a shared database, where "just add a column" breaks someone
  else's query).
- The cost is that cross-service consistency, which used to be a
  database transaction and a foreign key, now has to be solved at the
  application level — sagas, eventual consistency via events.
- There are now N databases to operate, back up, and monitor instead
  of one.

## 3. "How would you keep two databases in sync — say, Postgres and Elasticsearch for the same data?"

**Answer:**

- **Dual-write** (writing to both from the application) is simple but
  risky — a failure partway through leaves the two stores silently
  diverged, and there's no built-in detection of that drift.
- **Change Data Capture** (a tool like Debezium reading the Postgres
  write-ahead log) into a stream that asynchronously reindexes
  Elasticsearch is more robust — Postgres stays the single point of
  truth for the write, and the sync is driven by what actually
  committed, not by hoping both writes in the application succeeded.
- The trade-off either way is latency: there's always a window where a
  just-written row hasn't reached the search index yet.

---

## Summary

- CQRS, database-per-service, and CDC-based sync all buy independence
  and scalability by trading away immediate consistency — know what
  you're giving up, not just what you're gaining.
