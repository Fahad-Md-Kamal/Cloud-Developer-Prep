---
title: "Database Types: The Decision Framework"
---

# Database Types: The Decision Framework

"How many types of databases are there?" doesn't have a fixed official
answer — new categories get named as new access patterns become common
enough to deserve purpose-built storage. What's stable is the actual
question each category answers: every type below exists because some
workload's shape made the previous options genuinely worse, not because
someone wanted a new product category. This page is the map; each linked
chapter is the deep dive.

## 1. "Relational (SQL) — what's it built around, and when do you default to it?"

**Answer:**

- Built around **tables with enforced relationships** — foreign keys,
  constraints, and multi-row **ACID** (Atomicity, Consistency,
  Isolation, Durability) transactions that guarantee correctness even
  under concurrent writes. **SQL** (Structured Query Language) is the
  query language every database in this category speaks.
- Default choice whenever data has real relationships and correctness
  matters more than raw write throughput — orders, payments, inventory,
  anything where a half-applied transaction would be a real problem.
- Deep dive: [PostgreSQL for Scale](postgresql-for-scale.md),
  [SQL & Relational Data Modeling](sql-data-modeling-fundamentals.md).

## 2. "Document stores — what makes this a genuinely different shape, not just 'schema-less SQL'?"

**Answer:**

- Built around **data locality**: everything one query typically needs
  together (a user profile and their preferences, a product and its
  variants) lives in one self-contained document, avoiding a join.
- Earns its place when the access pattern is "fetch one document with
  everything it needs" and the schema genuinely varies per record — a
  product catalog, activity feeds, logs — not as a default replacement
  for relational modeling.
- Deep dive: [MongoDB for Scale](mongodb-for-scale.md).

## 3. "Key-value stores — what's the actual trade-off that makes them so fast?"

**Answer:**

- Built around **one operation**: look up a value by an exact key.
  There's no query language, no joins, no secondary indexing by
  default — that narrowness *is* the speed, not a limitation bolted on.
- Earns its place for session storage, rate limiting, leaderboards, and
  anything else genuinely key-value shaped, where a relational database's
  generality would just be unused overhead.
- Deep dive: [Redis as a Database](redis-as-a-database.md).

## 4. "Wide-column stores — how is this different from a document store?"

**Answer:**

- Built around **the query, not the entity** — data is deliberately
  denormalized and duplicated across tables, each shaped for one access
  pattern, specifically so a read never needs a cross-node join.
- Earns its place at a scale where joins across a distributed cluster
  would be genuinely too slow — very high write throughput spread across
  many nodes, with access patterns known in advance.
- Deep dive: [Wide-Column Stores (Cassandra)](wide-column-stores-cassandra.md).

## 5. "Graph databases — why would relationships need their own storage model?"

**Answer:**

- Built around **index-free adjacency** — each node stores direct
  pointers to its connected edges, so traversing a relationship is a
  pointer hop, not an index lookup that gets slower as the data grows.
- Earns its place when the *query itself* is about relationships —
  multi-hop "friend of a friend," fraud rings, recommendation graphs —
  where the equivalent SQL would be a chain of increasingly expensive
  self-joins.
- Deep dive: [Graph Databases (Neo4j)](graph-databases-neo4j.md).

## 6. "Vector databases — different from all of the above in what way?"

**Answer:**

- Built around **similarity search**, not exact match — given a query
  vector, find the stored vectors closest to it, the mechanism behind
  semantic search and **RAG** (Retrieval-Augmented Generation).
- The one category on this list that doesn't compete with the others
  directly — it typically sits alongside a relational or document store,
  handling the specific "find things that mean something similar" query
  the others aren't built for.
- Deep dive: [RAG & Vector Databases](../ai-llm/rag-and-vector-databases.md).

## 7. "Time-series databases — why not just use Postgres for timestamped data?"

**Answer:**

- Built around **near-constant appends** queried by time range and
  aggregation, with automatic data lifecycle (downsampling, retention)
  as a first-class feature rather than something you build yourself.
- Earns its place once the ingest rate and retention-policy complexity
  (keep raw data briefly, roll it up into coarser summaries long-term)
  outgrow what a general-purpose relational table handles cleanly.
- Deep dive: [Time-Series Databases](time-series-databases.md).

## 8. "Search engines (Elasticsearch/Solr) — isn't this just a document store with text search added?"

**Answer:**

- Built around the **inverted index** — mapping each word to every
  document containing it — a fundamentally different structure from a
  B-tree index, optimized for "find documents matching these terms,
  ranked by relevance," not for exact lookups or transactions.
- Earns its place for full-text search, relevance ranking, and faceted
  filtering — not as a system of record, since it trades away the strong
  consistency and transactional guarantees a database handling the
  authoritative data needs.
- Deep dive: [Elasticsearch Architecture](elasticsearch-architecture.md).

## 9. "NewSQL — how does it get both ACID and horizontal scale, when the categories above treat that as a trade-off?"

**Answer:**

- Built around **consensus protocols** (Raft/Paxos) replicating small
  data ranges across nodes, keeping the relational model and ACID
  transactions while scaling writes horizontally — the one category here
  that directly challenges the "pick consistency or scale" framing the
  others imply.
- Earns its place when a single-writer relational database's write path
  is the actual bottleneck, and strong consistency can't be relaxed —
  not simply "the site gets a lot of traffic."
- Deep dive: [NewSQL: Distributed SQL](newsql-distributed-sql.md).

## Putting it together

| Type | The question it answers | Reach for it when |
|---|---|---|
| Relational | "Keep this correct, with relationships, under concurrent writes" | Data has real relationships; correctness matters most |
| Document | "Fetch one self-contained record fast" | Per-record schema varies; access is mostly by ID |
| Key-value | "Look this up by exact key, as fast as possible" | The data and the query are genuinely key → value |
| Wide-column | "Scale writes across many nodes, by known query patterns" | Very high write volume, access patterns known upfront |
| Graph | "Traverse relationships, not rows" | The query itself is about connections, not records |
| Vector | "Find things that mean something similar" | Semantic search, RAG, recommendations by similarity |
| Time-series | "Append constantly, query by time range" | High-ingest timestamped data with a retention policy |
| Search engine | "Rank documents by relevance to these terms" | Full-text search, not a system of record |
| NewSQL | "Scale writes, keep ACID and SQL" | A single-writer relational DB's write path is the bottleneck |

No real production system picks exactly one — see
[Cross-Store Architecture Patterns](cross-store-architecture-patterns.md)
for how these actually get combined (and kept in sync) in practice.

---

## Code Samples

No dedicated code samples for this page — see each linked chapter's own
Code Samples section for runnable examples specific to that database
type.
