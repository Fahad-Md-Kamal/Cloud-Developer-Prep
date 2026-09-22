---
title: SQL
---

# SQL

## Checklist

- `INNER` vs `LEFT`/`RIGHT` vs `FULL OUTER` join — when each applies
- Indexing: when an index helps vs hurts, composite indexes,
  `EXPLAIN`/`EXPLAIN ANALYZE`
- Normalization (1NF–3NF) and when to deliberately denormalize
- Window functions (`ROW_NUMBER`, `RANK`, `PARTITION BY`) — common in
  senior-level tests
- Aggregate queries: `GROUP BY` + `HAVING` vs `WHERE`
- Transactions: isolation levels, deadlocks, `SELECT FOR UPDATE`
- Geospatial indexing (GiST) for spatial data — a differentiator most
  candidates won't have, worth mentioning if it comes up naturally

## Practice

Pick 2–3 medium-difficulty problems (joins + window functions) and solve
them without looking anything up, timed to ~10 minutes each. Good sources:
[PG Exercises](https://pgexercises.com/) for query volume, *Use The
Index, Luke* for reading query plans and indexes.
