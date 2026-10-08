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

## 4. "If you had to choose a database, which one would you choose, and why? Compare Postgres and MongoDB."

**Answer:**

- There's no universally "right" database — the real answer is the
  decision framework, not a single product name: what's the shape of
  the data (relational with real constraints vs. document-shaped,
  per-record schema variance), what's the access pattern (joins and
  multi-row transactions vs. fetch-by-ID and aggregation), and what
  consistency guarantee the use case actually needs.
- **Postgres** — strong relational integrity (foreign-key constraints,
  multi-row ACID transactions), a mature query planner, and `JSONB`
  for the semi-structured cases that do come up (see
  [PostgreSQL for Scale §5](postgresql-for-scale.md#5-when-does-jsonb-in-postgres-make-sense-vs-a-normalized-column-or-vs-reaching-for-mongo)).
  The default choice whenever data has real relationships and
  correctness constraints matter — orders, payments, inventory.
- **MongoDB** — schema-per-document flexibility, and horizontal write
  scaling via sharding is a more natural fit than it is in Postgres.
  Earns its place when the access pattern is genuinely
  "fetch one document with everything it needs" (catalog items,
  activity feeds, logs) rather than cross-entity joins.
- **The honest interview answer:** default to Postgres unless there's
  a specific reason not to — it's the mature default for most backend
  systems — and name MongoDB specifically when the schema volatility
  or access pattern earns it. "NoSQL scales better" as a blanket claim
  doesn't hold up: Postgres also scales horizontally via read replicas
  and partitioning (see
  [PostgreSQL for Scale §3](postgresql-for-scale.md#3-when-would-you-reach-for-table-partitioning-and-what-does-it-cost-you)).

## 5. "You're collecting raw, unstructured data now and plan to structure it and migrate it into a relational database later — how do you approach that?"

**Answer:**

- This is the schema-on-read → schema-on-write pipeline: land raw data
  first, in a store that doesn't demand a schema up front, rather than
  forcing a relational schema before the real shape of the incoming
  data is actually understood.
- Land it in a document store (MongoDB), object storage (S3) with a
  structured file format, or even an append-only raw table with a
  `JSONB` column in Postgres itself — whichever avoids rejecting data
  that doesn't fit a schema no one has designed yet.
- Once patterns stabilize — which fields are reliably present, which
  relationships are real rather than incidental — design the
  relational schema deliberately, instead of reverse-engineering it
  live under write pressure.
- Migrate via a backfill/ETL step that reads the raw store and writes
  normalized rows into the new schema — the same
  dual-write-then-backfill-then-cutover discipline as
  [Django & DRF's zero-downtime migration pattern](../programming-languages/python/django-drf.md#7-migrations),
  just moving data across stores instead of across one schema change.
- Keep the raw store as the source of truth until the relational side
  is verified correct against it — don't delete the only unstructured
  copy before the structured version has actually been validated.

---

## Summary

- CQRS, database-per-service, and CDC-based sync all buy independence
  and scalability by trading away immediate consistency — know what
  you're giving up, not just what you're gaining.
