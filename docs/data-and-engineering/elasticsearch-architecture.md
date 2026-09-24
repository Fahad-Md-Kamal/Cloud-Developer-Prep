---
title: "Elasticsearch Architecture"
---

# Elasticsearch Architecture

How Elasticsearch's query model differs from SQL, designing an index
under constant write and search load, and where Elasticsearch
belongs — and doesn't — in an overall data architecture.

## 1. "How is an Elasticsearch query fundamentally different from a SQL `WHERE` clause?"

```json
{"query": {"match": {"description": "wireless bluetooth headphones"}}}
{"query": {"term": {"status.keyword": "published"}}}
```

**Answer:**

- A SQL `WHERE` clause returns rows that exactly match a predicate —
  true or false, no ranking.
- A `match` query in Elasticsearch analyzes and tokenizes the search
  text, then returns documents *ranked* by relevance (BM25 scoring),
  not a boolean match — there's no single "the" answer, only a
  best-ranked list.
- `term` queries are the exception, matching exactly against an
  unanalyzed `keyword` field.
- The mapping decision — whether a field is `text` (analyzed,
  searchable) or `keyword` (exact-match, aggregatable) — is made at
  index time, and getting it wrong means a reindex to fix, not a query
  change.

## 2. "How would you design an index for a system that's both written to and searched constantly?"

**Answer:**

- Tune `refresh_interval` up (documents become searchable slightly
  later) to reduce the write-side cost of making every write
  immediately visible.
- Use index aliases so a reindex (changing a mapping, say) can happen
  behind the scenes and be swapped in atomically with zero downtime
  for readers.
- For time-series-shaped data, use Index Lifecycle Management to age
  data through hot → warm → cold tiers with cheaper hardware and fewer
  replicas as it gets less relevant to active search.
- Replica count is a direct trade-off: more replicas means more read
  throughput and resilience, at the cost of more write amplification
  (every write replicated to every copy).

| Pros | Cons / Trade-offs |
|---|---|
| ILM keeps old data cheap without deleting it outright | More moving infrastructure (tiers, aliases) to operate correctly |
| Aliases enable zero-downtime remapping/reindexing | Extra indirection — "which concrete index is this alias pointing at right now" |
| Replica count tunable per read/write balance needed | Every replica multiplies write cost, not just storage |

## 3. "When would you use Elasticsearch as a system of record vs. just a search index?"

**Answer:**

- Almost never as the sole system of record — it doesn't give the
  ACID transactional guarantees or the same durability story as
  Postgres or Mongo.
- The standard architecture keeps a real database as the source of
  truth and syncs data into Elasticsearch purely for what it's good
  at: full-text search and aggregations over large volumes.
- Losing an Elasticsearch index should mean "reindex from the source
  of truth," never "lost data."

---

## Summary

- Built for ranked full-text search and aggregation at scale, not as a
  transactional system of record.
- Index design (mappings, ILM, aliases) is a decision made largely up
  front — getting the mapping wrong later costs a reindex, not a
  query fix.
