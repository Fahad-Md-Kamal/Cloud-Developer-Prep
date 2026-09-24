---
title: "PostgreSQL for Scale"
---

# PostgreSQL for Scale

Indexing, query diagnosis, partitioning, replication, JSONB, and
Django ORM query cost — the PostgreSQL questions that come up cold in
a senior interview, each with the trade-offs named explicitly.

## 1. "Walk me through choosing an index — B-tree vs. GIN vs. GiST."

```sql
-- B-tree: the default, for equality/range on scalar columns
CREATE INDEX idx_orders_created_at ON orders (created_at);

-- GIN: for containment queries on JSONB, arrays, and full-text search
CREATE INDEX idx_orders_metadata ON orders USING GIN (metadata jsonb_path_ops);

-- GiST: for geometric types, ranges, and nearest-neighbor queries
CREATE INDEX idx_venues_location ON venues USING GiST (location);
```

**Answer:**

- B-tree is the right default for equality and range lookups on
  ordinary scalar columns — it's what you get without specifying
  anything, and it covers the large majority of indexing needs.
- GIN earns its keep on composite/multi-valued data: `JSONB`
  containment (`@>`), array membership, or full-text search vectors,
  where a B-tree can't express the query at all.
- GiST fits geometric and range types, and supports
  approximate/nearest-neighbor operators GIN doesn't.
- The practical mistake isn't picking the wrong one of these three —
  it's adding an index without first looking at what the query
  actually filters, joins, or orders on.

| Pros | Cons / Trade-offs |
|---|---|
| Right index type turns a sequential scan into an index scan | Every index slows down writes — more structures to update per `INSERT`/`UPDATE` |
| GIN/GiST enable queries a B-tree structurally can't answer | GIN indexes are larger and slower to build than B-tree for the same data |
| Composite/partial indexes can target the exact query shape in use | An unused index is pure cost — no query benefit, still paid on every write |

## 2. "How do you find out why a query is slow, instead of guessing?"

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE customer_id = 42 AND status = 'pending';
```

**Answer:**

- Run `EXPLAIN (ANALYZE, BUFFERS)` and compare the planner's
  *estimated* row count against the *actual* row count at each node.
- A big gap usually means stale statistics (`ANALYZE` the table)
  rather than a genuinely bad plan.
- Look for a sequential scan where an index scan was expected, and
  check `BUFFERS` for how much came from disk versus cache.
- Guessing at "add an index" or "denormalize this" without first
  looking at the actual plan is the single most common way engineers
  waste time optimizing the wrong thing.

## 3. "When would you reach for table partitioning, and what does it cost you?"

**Answer:**

- Reach for it when a table is large enough that most queries only
  ever touch a slice of it — typically time-series data filtered by
  date — and that slice lines up with a natural partition key.
- Range-partitioning by month means a query for "last 30 days" only
  scans one or two partitions instead of the whole table (partition
  pruning), and old partitions can be dropped instantly instead of run
  through a slow `DELETE`.
- The cost: any unique constraint or index must include the partition
  key, cross-partition queries and joins get harder to reason about,
  and migrating an existing large table into partitions is itself a
  real, careful piece of operational work — not a config flag.

| Pros | Cons / Trade-offs |
|---|---|
| Partition pruning skips irrelevant partitions entirely | Unique constraints/PKs must include the partition key |
| Dropping an old partition is instant vs. a slow bulk `DELETE` | Cross-partition queries and joins are harder to optimize |
| Vacuum/maintenance can operate per-partition | Migrating an existing large table into partitions is a real, risky project |

## 4. "Explain PostgreSQL replication for HA — what's the actual failover story?"

**Answer:**

- Streaming replication ships the WAL to one or more replicas
  continuously.
- **Asynchronous** replication is the default — the primary doesn't
  wait for a replica to confirm, so a crash can lose the last few
  committed transactions that hadn't shipped yet.
- **Synchronous** replication waits for at least one replica to
  confirm before acknowledging the commit — zero data loss on
  failover, at the cost of added write latency and the primary
  blocking if that replica is slow or down.
- Either way, PostgreSQL itself does **not** auto-promote a replica on
  primary failure — that requires an external tool (Patroni, repmgr,
  or a cloud provider's managed failover) watching health and doing
  the promotion and DNS/connection redirect.

## 5. "When does JSONB in Postgres make sense vs. a normalized column, or vs. reaching for Mongo?"

```sql
CREATE INDEX idx_orders_metadata_gin ON orders USING GIN (metadata jsonb_path_ops);
SELECT * FROM orders WHERE metadata @> '{"source": "mobile_app"}';
```

**Answer:**

- `JSONB` is a good fit for attributes that are genuinely sparse or
  variable across rows and queried only occasionally — it saves a
  schema migration for every new optional field.
- The moment a field inside that JSON is filtered, joined, or ordered
  on *constantly*, it should be promoted to a real, indexed column — a
  GIN index on JSONB helps but never beats a proper B-tree on a
  first-class column.
- None of this is a reason to reach for MongoDB instead: JSONB gives
  flexible schema *inside* a single ACID, transactional database,
  which is a different trade-off than moving the data to a separate
  store entirely.

## 6. "How do you keep Django ORM query count and SQL cost under control at scale?"

In Django systems, database performance problems usually come from
the boundary between ORM usage and PostgreSQL execution — reasoning
about both layers together is the actual skill being tested.

```python
from django.db.models import Count, F, Q

accounts = (
    Account.objects
    .filter(is_active=True)
    .annotate(
        open_invoice_count=Count(
            "invoices",
            filter=Q(invoices__status="open")
        ),
        available_credit=F("credit_limit") - F("used_credit"),
    )
    .order_by("-available_credit")
)
```

**Answer:**

- Push computation into SQL instead of looping in Python — the query
  above combines filtering, an aggregate with its own `Q` filter, and
  a computed field (`F` expressions) without ever pulling raw rows
  into Python to do that math.
- `select_related` (SQL `JOIN`, for forward/one-to-one relations) and
  `prefetch_related` (a second query, for reverse/many-to-many
  relations) are what actually fix the classic N+1 pattern — one query
  per related object accessed in a loop.
- Choose indexes based on the filters/joins/ordering a query
  *actually* uses, confirm with `EXPLAIN` rather than guessing.
- Reach for row locks (`select_for_update`) only where correctness
  genuinely requires them, since they trade throughput for
  consistency.

**Likely follow-up — "what's the cost of `select_for_update` under contention?"**

- It serializes access to the locked rows — every other transaction
  wanting the same row blocks until the lock is released, which is
  correct but throttles throughput hard on a hot row.
- Scope it to the narrowest row set and the shortest transaction
  possible.

---

## Summary

- Index type follows the actual query shape, not a default habit;
  `EXPLAIN ANALYZE` replaces guessing; partitioning and replication
  both trade real operational complexity for real scaling headroom.
- Django ORM: push aggregation and computed fields into SQL, fix N+1
  with `select_related`/`prefetch_related`, and reach for row locks
  only when correctness genuinely demands them.

---

## Practice Notes (from live session)

### SQL practice sandbox

A real SQLite database (`employees`/`departments`, seeded with deliberate
salary ties) plus an 8-problem set (joins through
`RANK`/`ROW_NUMBER`/`LAG`/`LEAD`) and verified solutions live in this
repo at [`practice/sql/`](https://github.com/Fahad-Md-Kamal/Cloud-Developer-Prep/tree/main/practice/sql):

```bash
cd practice/sql
sqlite3 practice.db < schema.sql   # one-time setup
sqlite3 practice.db                # open the shell and start querying
```

Beyond that, [PG Exercises](https://pgexercises.com/) for more query
volume, *Use The Index, Luke* for reading query plans and indexes.

### Worked example: rank within a group (window functions)

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

#### Tracing it on real data

Abstract syntax doesn't stick — trace it on actual rows instead.

**Sample data:**

| name | department_id | salary |
|---|---|---|
| Alice | 10 | 90000 |
| Bob | 10 | 80000 |
| Carol | 10 | 80000 |
| Dave | 20 | 70000 |
| Eve | 20 | 60000 |

Running `RANK() OVER (PARTITION BY department_id ORDER BY salary DESC)`
produces:

| name | department_id | salary | salary_rank |
|---|---|---|---|
| Alice | 10 | 90000 | 1 |
| Bob | 10 | 80000 | 2 |
| Carol | 10 | 80000 | 2 |
| Dave | 20 | 70000 | 1 |
| Eve | 20 | 60000 | 2 |

**Step by step:**

1. **`PARTITION BY department_id`** — mentally split the table into
   buckets, one per department. Nothing is deleted or merged; every row
   is still there.
2. **`ORDER BY salary DESC`** (inside `OVER(...)`) — within *each bucket
   separately*, sort by salary, highest first.
3. **`RANK()`** — walk down each bucket's sorted order and assign 1st,
   2nd, etc., restarting at 1 every time you cross into a new bucket.
   Tied rows (Bob and Carol, both 80000) get the same rank.

**Why not plain `ORDER BY` + row position?** That gives one ranking
across the *whole table* (Alice would be #1 overall, Dave #4 overall).
`RANK() OVER (PARTITION BY ...)` gives a ranking that resets **per
group**, in a single query, without collapsing rows the way `GROUP BY`
would.

**The core idea, stated generally:** `PARTITION BY` splits the result
set into groups — here, one per department — **without collapsing rows**
the way `GROUP BY` does (`GROUP BY` produces one row per group; a window
function keeps every row and just annotates it). `ORDER BY salary DESC`
inside the `OVER (...)` clause then ranks rows within each partition.

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
