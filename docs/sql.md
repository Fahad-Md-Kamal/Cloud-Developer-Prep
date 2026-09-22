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

## Worked example: rank within a group (window functions)

Schema: `employees(id, name, department_id, salary, hire_date)`,
`departments(id, name)`.

**Task:** each employee's name, department name, salary, and their salary
rank *within their department* (1 = highest paid), ordered by department
then rank.

```sql
SELECT
    e.name,
    d.name AS department_name,
    e.salary,
    RANK() OVER (PARTITION BY e.department_id ORDER BY e.salary DESC) AS salary_rank
FROM employees e
JOIN departments d ON e.department_id = d.id
ORDER BY d.name, salary_rank;
```

**The core idea:** `PARTITION BY` splits the result set into groups —
here, one per department — **without collapsing rows** the way
`GROUP BY` does (`GROUP BY` produces one row per group; a window function
keeps every row and just annotates it). `ORDER BY salary DESC` inside the
`OVER (...)` clause then ranks rows within each partition.

**Tie handling — the other thing this tests:**

| Function | Ties | Next rank after a tie |
|---|---|---|
| `ROW_NUMBER()` | always unique (1,2,3,4...) | n/a |
| `RANK()` | same rank | **skips** (1,1,3,4) |
| `DENSE_RANK()` | same rank | **doesn't skip** (1,1,2,3) |

!!! note "Session note"
    Covered in the [session log](session-log.md#2026-09-22) — first
    attempt used `GROUP BY` (wrong tool: collapses rows instead of
    ranking within them) with no join and no window function. Flagged
    for another rep before the real interview.
